from flask import Blueprint, render_template, request, redirect, url_for, flash
import sqlite3
from flask import current_app

automation_bp = Blueprint("automation", __name__, url_prefix="/automation")


def get_db():
    db = sqlite3.connect(current_app.config["DATABASE_PATH"])
    db.row_factory = sqlite3.Row
    return db


def ensure_schedule_columns(db):
    """Add scheduling columns if they do not already exist."""
    columns = db.execute("PRAGMA table_info(automations)").fetchall()
    column_names = [column["name"] for column in columns]

    if "scheduled_time" not in column_names:
        db.execute(
            "ALTER TABLE automations ADD COLUMN scheduled_time TEXT"
        )

    if "last_run_at" not in column_names:
        db.execute(
            "ALTER TABLE automations ADD COLUMN last_run_at TEXT"
        )

    db.commit()


@automation_bp.route("/", methods=["GET", "POST"])
def automation():
    db = get_db()

    ensure_schedule_columns(db)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        trigger_type = request.form.get("trigger_type", "").strip()
        scheduled_time = request.form.get("scheduled_time", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not subject or not message:
            db.close()
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("automation.automation"))

        db.execute(
            """
            INSERT INTO automations
            (name, trigger_type, subject, message, active, created_at,
             scheduled_time, last_run_at)
            VALUES (?, ?, ?, ?, 1, datetime('now'), ?, NULL)
            """,
            (
                name,
                trigger_type,
                subject,
                message,
                scheduled_time if trigger_type == "Scheduled Time" else None,
            ),
        )

        db.commit()
        db.close()

        flash("Automation created successfully!", "success")
        return redirect(url_for("automation.automation"))

    automations = db.execute(
        """
        SELECT id, name, trigger_type, subject, message,
               active, created_at, scheduled_time, last_run_at
        FROM automations
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "automation.html",
        automations=automations
    )


@automation_bp.route("/<int:automation_id>/toggle", methods=["POST"])
def toggle_automation(automation_id):
    db = get_db()

    automation = db.execute(
        "SELECT active FROM automations WHERE id = ?",
        (automation_id,)
    ).fetchone()

    if automation:
        new_status = 0 if automation["active"] else 1

        db.execute(
            "UPDATE automations SET active = ? WHERE id = ?",
            (new_status, automation_id)
        )

        db.commit()

        if new_status:
            flash("Automation enabled.", "success")
        else:
            flash("Automation disabled.", "success")
    else:
        flash("Automation not found.", "danger")

    db.close()

    return redirect(url_for("automation.automation"))