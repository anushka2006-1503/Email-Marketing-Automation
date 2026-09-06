from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

import models

campaigns_bp = Blueprint("campaigns", __name__, url_prefix="/campaigns")


def _form_contact_ids():
    raw = request.form.getlist("contact_ids")
    return [int(value) for value in raw if str(value).isdigit()]


def _campaign_payload():
    template_id = request.form.get("template_id") or None
    if template_id:
        template_id = int(template_id)
    scheduled_raw = request.form.get("scheduled_at", "").strip()
    scheduled_at = None
    if scheduled_raw:
        parsed = models.parse_datetime(scheduled_raw)
        scheduled_at = parsed.strftime("%Y-%m-%d %H:%M:%S") if parsed else None
    return {
        "name": request.form.get("name", ""),
        "subject": request.form.get("subject", ""),
        "content": request.form.get("content", ""),
        "template_id": template_id,
        "contact_ids": _form_contact_ids(),
        "scheduled_at": scheduled_at,
    }


def _status_from_action(action, scheduled_at):
    if action == "send":
        return "Draft"
    if action == "schedule":
        return "Scheduled"
    if scheduled_at:
        return "Scheduled"
    return "Draft"


@campaigns_bp.route("/")
def list_campaigns():
    campaigns = models.list_campaigns()
    return render_template("campaigns/list.html", campaigns=campaigns)


@campaigns_bp.route("/add", methods=["GET", "POST"])
def add_campaign():
    contacts = models.list_contacts()
    templates = models.list_templates()
    if request.method == "POST":
        payload = _campaign_payload()
        action = request.form.get("action", "draft")
        if action == "schedule" and not payload["scheduled_at"]:
            flash("Choose a date and time to schedule this campaign.", "danger")
            return render_template(
                "campaigns/form.html",
                campaign=None,
                contacts=contacts,
                templates=templates,
                selected_ids=payload["contact_ids"],
                title="Create campaign",
            )
        if not payload["contact_ids"]:
            flash("Select at least one recipient.", "danger")
            return render_template(
                "campaigns/form.html",
                campaign=None,
                contacts=contacts,
                templates=templates,
                selected_ids=payload["contact_ids"],
                title="Create campaign",
            )
        status = _status_from_action(action, payload["scheduled_at"])
        campaign_id = models.create_campaign(
            payload["name"],
            payload["subject"],
            payload["content"],
            payload["template_id"],
            payload["contact_ids"],
            status,
            payload["scheduled_at"],
        )
        if action == "send":
            sent, total = models.dispatch_campaign(campaign_id)
            flash(f"Campaign sent to {sent} of {total} recipients.", "success")
            return redirect(url_for("campaigns.view_campaign", campaign_id=campaign_id))
        flash("Campaign saved." if status == "Draft" else "Campaign scheduled.", "success")
        return redirect(url_for("campaigns.list_campaigns"))
    return render_template(
        "campaigns/form.html",
        campaign=None,
        contacts=contacts,
        templates=templates,
        selected_ids=[],
        title="Create campaign",
    )


@campaigns_bp.route("/<int:campaign_id>")
def view_campaign(campaign_id):
    campaign = models.get_campaign(campaign_id)
    if not campaign:
        flash("Campaign not found.", "danger")
        return redirect(url_for("campaigns.list_campaigns"))
    recipients = models.get_campaign_recipients(campaign_id)
    logs = models.get_campaign_logs(campaign_id)
    return render_template(
        "campaigns/view.html",
        campaign=campaign,
        recipients=recipients,
        logs=logs,
    )


@campaigns_bp.route("/<int:campaign_id>/edit", methods=["GET", "POST"])
def edit_campaign(campaign_id):
    campaign = models.get_campaign(campaign_id)
    if not campaign:
        flash("Campaign not found.", "danger")
        return redirect(url_for("campaigns.list_campaigns"))
    if campaign["status"] == "Sent":
        flash("Sent campaigns cannot be edited.", "warning")
        return redirect(url_for("campaigns.view_campaign", campaign_id=campaign_id))
    contacts = models.list_contacts()
    templates = models.list_templates()
    if request.method == "POST":
        payload = _campaign_payload()
        action = request.form.get("action", "draft")
        if action == "schedule" and not payload["scheduled_at"]:
            flash("Choose a date and time to schedule this campaign.", "danger")
            return render_template(
                "campaigns/form.html",
                campaign=campaign,
                contacts=contacts,
                templates=templates,
                selected_ids=payload["contact_ids"],
                title="Edit campaign",
            )
        if not payload["contact_ids"]:
            flash("Select at least one recipient.", "danger")
            return render_template(
                "campaigns/form.html",
                campaign=campaign,
                contacts=contacts,
                templates=templates,
                selected_ids=payload["contact_ids"],
                title="Edit campaign",
            )
        status = _status_from_action(action, payload["scheduled_at"])
        models.update_campaign(
            campaign_id,
            payload["name"],
            payload["subject"],
            payload["content"],
            payload["template_id"],
            payload["contact_ids"],
            status,
            payload["scheduled_at"],
        )
        if action == "send":
            sent, total = models.dispatch_campaign(campaign_id)
            flash(f"Campaign sent to {sent} of {total} recipients.", "success")
            return redirect(url_for("campaigns.view_campaign", campaign_id=campaign_id))
        flash("Campaign updated.", "success")
        return redirect(url_for("campaigns.list_campaigns"))
    return render_template(
        "campaigns/form.html",
        campaign=campaign,
        contacts=contacts,
        templates=templates,
        selected_ids=models.get_campaign_recipient_ids(campaign_id),
        title="Edit campaign",
    )


@campaigns_bp.route("/<int:campaign_id>/send", methods=["POST"])
def send_campaign(campaign_id):
    campaign = models.get_campaign(campaign_id)
    if not campaign:
        flash("Campaign not found.", "danger")
        return redirect(url_for("campaigns.list_campaigns"))
    if campaign["status"] == "Sent":
        flash("This campaign was already sent.", "warning")
        return redirect(url_for("campaigns.view_campaign", campaign_id=campaign_id))
    sent, total = models.dispatch_campaign(campaign_id)
    flash(f"Campaign sent to {sent} of {total} recipients.", "success")
    return redirect(url_for("campaigns.view_campaign", campaign_id=campaign_id))


@campaigns_bp.route("/<int:campaign_id>/delete", methods=["POST"])
def delete_campaign(campaign_id):
    models.delete_campaign(campaign_id)
    flash("Campaign deleted.", "success")
    return redirect(url_for("campaigns.list_campaigns"))


@campaigns_bp.route("/template/<int:template_id>.json")
def template_json(template_id):
    template = models.get_template(template_id)
    if not template:
        return jsonify({}), 404
    return jsonify({"subject": template["subject"], "content": template["content"]})
