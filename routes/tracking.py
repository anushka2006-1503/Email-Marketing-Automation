from flask import Blueprint, Response, redirect, request

from database import get_db


tracking_bp = Blueprint("tracking", __name__, url_prefix="/track")


@tracking_bp.route("/open/<int:campaign_id>/<int:log_id>")
def track_open(campaign_id, log_id):
    db = get_db()

    db.execute(
        """
        UPDATE email_logs
        SET opened = 1
        WHERE id = ? AND campaign_id = ?
        """,
        (log_id, campaign_id),
    )
    db.commit()

    pixel = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
        b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
        b"\x00\x00\x00\x00,\x00\x00\x00\x00"
        b"\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )

    return Response(
        pixel,
        mimetype="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@tracking_bp.route("/click/<int:campaign_id>/<int:log_id>")
def track_click(campaign_id, log_id):
    target_url = request.args.get("url", "").strip()

    if not target_url.startswith(("http://", "https://")):
        return "Invalid URL", 400

    db = get_db()

    db.execute(
        """
        UPDATE email_logs
        SET clicked = 1
        WHERE id = ? AND campaign_id = ?
        """,
        (log_id, campaign_id),
    )
    db.commit()

    return redirect(target_url)