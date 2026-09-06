import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app


def send_email(to_address, subject, html_body):
    """Send via SMTP when configured; otherwise record as a local delivery."""
    cfg = current_app.config
    if not cfg.get("SMTP_HOST"):
        return True, "Logged locally (SMTP not configured)"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = cfg["SMTP_FROM"]
    message["To"] = to_address
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as server:
            if cfg.get("SMTP_USE_TLS"):
                server.starttls()
            if cfg.get("SMTP_USER"):
                server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            server.sendmail(cfg["SMTP_FROM"], [to_address], message.as_string())
        return True, "Sent via SMTP"
    except OSError as exc:
        return False, str(exc)
