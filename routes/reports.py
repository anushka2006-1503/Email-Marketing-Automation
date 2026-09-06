from flask import Blueprint, render_template

import models


reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
def report():
    analytics = models.analytics_stats()

    return render_template(
        "report.html",
        analytics=analytics,
    )