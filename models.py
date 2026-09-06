from datetime import datetime
import re
from urllib.parse import quote
from flask import url_for
from database import get_db
from mailer import send_email


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(value):
    if not value:
        return None
    value = value.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def to_datetime_local(value):
    if not value:
        return ""
    parsed = parse_datetime(value)
    if not parsed:
        return ""
    return parsed.strftime("%Y-%m-%dT%H:%M")


# --- Contacts ---


def list_contacts(search=""):
    db = get_db()
    if search:
        like = f"%{search}%"
        return db.execute(
            """
            SELECT * FROM contacts
            WHERE name LIKE ? OR email LIKE ? OR company LIKE ? OR phone LIKE ?
            ORDER BY name COLLATE NOCASE
            """,
            (like, like, like, like),
        ).fetchall()
    return db.execute("SELECT * FROM contacts ORDER BY name COLLATE NOCASE").fetchall()


def get_contact(contact_id):
    return get_db().execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()


def create_contact(name, email, phone, company, notes):
    db = get_db()
    db.execute(
        """
        INSERT INTO contacts (name, email, phone, company, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name.strip(), email.strip().lower(), phone.strip(), company.strip(), notes.strip(), now_iso()),
    )
    db.commit()


def update_contact(contact_id, name, email, phone, company, notes):
    db = get_db()
    db.execute(
        """
        UPDATE contacts
        SET name = ?, email = ?, phone = ?, company = ?, notes = ?
        WHERE id = ?
        """,
        (name.strip(), email.strip().lower(), phone.strip(), company.strip(), notes.strip(), contact_id),
    )
    db.commit()


def delete_contact(contact_id):
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    db.commit()


# --- Templates ---


def list_templates():
    return get_db().execute(
        "SELECT * FROM email_templates ORDER BY updated_at DESC"
    ).fetchall()


def get_template(template_id):
    return get_db().execute(
        "SELECT * FROM email_templates WHERE id = ?", (template_id,)
    ).fetchone()


def create_template(name, subject, content):
    db = get_db()
    stamp = now_iso()
    db.execute(
        """
        INSERT INTO email_templates (name, subject, content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name.strip(), subject.strip(), content, stamp, stamp),
    )
    db.commit()


def update_template(template_id, name, subject, content):
    db = get_db()
    db.execute(
        """
        UPDATE email_templates
        SET name = ?, subject = ?, content = ?, updated_at = ?
        WHERE id = ?
        """,
        (name.strip(), subject.strip(), content, now_iso(), template_id),
    )
    db.commit()


def delete_template(template_id):
    db = get_db()
    db.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
    db.commit()


# --- Campaigns ---


def list_campaigns():
    return get_db().execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM campaign_recipients cr WHERE cr.campaign_id = c.id) AS recipient_count
        FROM campaigns c
        ORDER BY c.created_at DESC
        """
    ).fetchall()


def get_campaign(campaign_id):
    return get_db().execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()


def get_campaign_recipient_ids(campaign_id):
    rows = get_db().execute(
        "SELECT contact_id FROM campaign_recipients WHERE campaign_id = ?",
        (campaign_id,),
    ).fetchall()
    return [row["contact_id"] for row in rows]


def get_campaign_recipients(campaign_id):
    return get_db().execute(
        """
        SELECT contacts.*
        FROM contacts
        JOIN campaign_recipients ON contacts.id = campaign_recipients.contact_id
        WHERE campaign_recipients.campaign_id = ?
        ORDER BY contacts.name COLLATE NOCASE
        """,
        (campaign_id,),
    ).fetchall()


def get_campaign_logs(campaign_id):
    return get_db().execute(
        "SELECT * FROM email_logs WHERE campaign_id = ? ORDER BY sent_at DESC",
        (campaign_id,),
    ).fetchall()


def _set_recipients(db, campaign_id, contact_ids):
    db.execute("DELETE FROM campaign_recipients WHERE campaign_id = ?", (campaign_id,))
    for contact_id in contact_ids:
        db.execute(
            "INSERT INTO campaign_recipients (campaign_id, contact_id) VALUES (?, ?)",
            (campaign_id, contact_id),
        )


def create_campaign(name, subject, content, template_id, contact_ids, status, scheduled_at):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO campaigns (name, subject, content, template_id, status, scheduled_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name.strip(), subject.strip(), content, template_id, status, scheduled_at, now_iso()),
    )
    campaign_id = cursor.lastrowid
    _set_recipients(db, campaign_id, contact_ids)
    db.commit()
    return campaign_id


def update_campaign(campaign_id, name, subject, content, template_id, contact_ids, status, scheduled_at):
    db = get_db()
    db.execute(
        """
        UPDATE campaigns
        SET name = ?, subject = ?, content = ?, template_id = ?, status = ?, scheduled_at = ?
        WHERE id = ?
        """,
        (name.strip(), subject.strip(), content, template_id, status, scheduled_at, campaign_id),
    )
    _set_recipients(db, campaign_id, contact_ids)
    db.commit()


def delete_campaign(campaign_id):
    db = get_db()
    db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    db.commit()


def dispatch_campaign(campaign_id):
    db = get_db()
    campaign = get_campaign(campaign_id)
    recipients = get_campaign_recipients(campaign_id)
    sent_count = 0

    for contact in recipients:
        body = (
            campaign["content"]
            .replace("{{name}}", contact["name"] or "")
            .replace("{{email}}", contact["email"] or "")
            .replace("{{company}}", contact["company"] or "")
        )

        # Create the email log first so we have a log ID for tracking.
        cursor = db.execute(
            """
            INSERT INTO email_logs
            (campaign_id, contact_id, email, sent_at, status, detail, opened, clicked)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (
                campaign_id,
                contact["id"],
                contact["email"],
                now_iso(),
                "pending",
                "",
            ),
        )

        log_id = cursor.lastrowid

        # Add click tracking to normal HTTP/HTTPS links.
        def replace_link(match):
            prefix = match.group(1)
            target_url = match.group(2)
            suffix = match.group(3)

            if target_url.startswith(("http://", "https://")):
                tracked_url = url_for(
                    "tracking.track_click",
                    campaign_id=campaign_id,
                    log_id=log_id,
                    url=target_url,
                    _external=True,
                )
                return f"{prefix}{tracked_url}{suffix}"

            return match.group(0)

        body = re.sub(
            r'(href=["\'])([^"\']+)(["\'])',
            replace_link,
            body,
            flags=re.IGNORECASE,
        )

        # Add a 1x1 tracking pixel for open tracking.
        tracking_pixel = url_for(
            "tracking.track_open",
            campaign_id=campaign_id,
            log_id=log_id,
            _external=True,
        )

        body += (
            f'<img src="{tracking_pixel}" '
            'width="1" height="1" style="display:none;" alt="">'
        )

        ok, detail = send_email(
            contact["email"],
            campaign["subject"],
            body,
        )

        db.execute(
            """
            UPDATE email_logs
            SET status = ?, detail = ?, sent_at = ?
            WHERE id = ?
            """,
            (
                "sent" if ok else "failed",
                detail,
                now_iso(),
                log_id,
            ),
        )

        if ok:
            sent_count += 1

    db.execute(
        """
        UPDATE campaigns
        SET status = 'Sent', sent_at = ?, emails_sent = ?
        WHERE id = ?
        """,
        (now_iso(), sent_count, campaign_id),
    )

    db.commit()

    return sent_count, len(recipients)

def process_due_campaigns():
    db = get_db()
    due = db.execute(
        """
        SELECT id FROM campaigns
        WHERE status = 'Scheduled'
          AND scheduled_at IS NOT NULL
          AND scheduled_at <= ?
        """,
        (now_iso(),),
    ).fetchall()
    for row in due:
        dispatch_campaign(row["id"])


# --- Dashboard ---


def dashboard_stats():
    db = get_db()
    contacts = db.execute("SELECT COUNT(*) AS n FROM contacts").fetchone()["n"]
    campaigns = db.execute("SELECT COUNT(*) AS n FROM campaigns").fetchone()["n"]
    emails_sent = db.execute(
        "SELECT COALESCE(SUM(emails_sent), 0) AS n FROM campaigns"
    ).fetchone()["n"]
    scheduled = db.execute(
        "SELECT COUNT(*) AS n FROM campaigns WHERE status = 'Scheduled'"
    ).fetchone()["n"]
    recent = db.execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM campaign_recipients cr WHERE cr.campaign_id = c.id) AS recipient_count
        FROM campaigns c
        ORDER BY c.created_at DESC
        LIMIT 5
        """
    ).fetchall()
    upcoming = db.execute(
        """
        SELECT * FROM campaigns
        WHERE status = 'Scheduled'
        ORDER BY scheduled_at ASC
        LIMIT 5
        """
    ).fetchall()
    return {
        "contacts": contacts,
        "campaigns": campaigns,
        "emails_sent": emails_sent,
        "scheduled": scheduled,
        "recent": recent,
        "upcoming": upcoming,
    }

def analytics_stats():
    db = get_db()

    total_contacts = db.execute(
        "SELECT COUNT(*) AS n FROM contacts"
    ).fetchone()["n"]

    total_sent = db.execute(
        "SELECT COUNT(*) AS n FROM email_logs WHERE status = 'sent'"
    ).fetchone()["n"]

    total_failed = db.execute(
        "SELECT COUNT(*) AS n FROM email_logs WHERE status = 'failed'"
    ).fetchone()["n"]
    total_opened = db.execute(
        "SELECT COUNT(*) AS n FROM email_logs WHERE opened = 1"
    ).fetchone()["n"]

    total_clicked = db.execute(
        "SELECT COUNT(*) AS n FROM email_logs WHERE clicked = 1"
    ).fetchone()["n"]
    total_logs = total_sent + total_failed

    delivery_rate = round(
        (total_sent / total_logs * 100), 2
    ) if total_logs else 0
    open_rate = round(
        (total_opened / total_sent * 100), 2
    ) if total_sent else 0

    click_rate = round(
        (total_clicked / total_sent * 100), 2
    ) if total_sent else 0
    campaign_performance = db.execute(
        """
        SELECT
            c.id,
            c.name,
            c.subject,
            c.status,
            c.emails_sent,
            (
                SELECT COUNT(*)
                FROM campaign_recipients cr
                WHERE cr.campaign_id = c.id
            ) AS recipients
        FROM campaigns c
        ORDER BY c.created_at DESC
        """
    ).fetchall()

    subscriber_growth = db.execute(
        """
        SELECT
            DATE(created_at) AS date,
            COUNT(*) AS count
        FROM contacts
        GROUP BY DATE(created_at)
        ORDER BY date ASC
        """
    ).fetchall()

    return {
        "total_contacts": total_contacts,
        "total_sent": total_sent,
        "total_failed": total_failed,
        "delivery_rate": delivery_rate,
        "total_opened": total_opened,
        "total_clicked": total_clicked,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "campaign_performance": campaign_performance,
        "subscriber_growth": subscriber_growth,
    }



















































































