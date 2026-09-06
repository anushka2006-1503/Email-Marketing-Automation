from flask import Blueprint, flash, redirect, render_template, request, url_for

import models

templates_bp = Blueprint("templates_bp", __name__, url_prefix="/templates")


@templates_bp.route("/")
def list_templates():
    templates = models.list_templates()
    return render_template("email_templates/list.html", templates=templates)


@templates_bp.route("/add", methods=["GET", "POST"])
def add_template():
    if request.method == "POST":
        models.create_template(
            request.form.get("name", ""),
            request.form.get("subject", ""),
            request.form.get("content", ""),
        )
        flash("Template saved.", "success")
        return redirect(url_for("templates_bp.list_templates"))
    return render_template("email_templates/form.html", template=None, title="New template")


@templates_bp.route("/<int:template_id>/edit", methods=["GET", "POST"])
def edit_template(template_id):
    template = models.get_template(template_id)
    if not template:
        flash("Template not found.", "danger")
        return redirect(url_for("templates_bp.list_templates"))
    if request.method == "POST":
        models.update_template(
            template_id,
            request.form.get("name", ""),
            request.form.get("subject", ""),
            request.form.get("content", ""),
        )
        flash("Template updated.", "success")
        return redirect(url_for("templates_bp.list_templates"))
    return render_template("email_templates/form.html", template=template, title="Edit template")


@templates_bp.route("/<int:template_id>/delete", methods=["POST"])
def delete_template(template_id):
    models.delete_template(template_id)
    flash("Template deleted.", "success")
    return redirect(url_for("templates_bp.list_templates"))
