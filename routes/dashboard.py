from flask import Blueprint, render_template

import models

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    stats = models.dashboard_stats()
    analytics = models.analytics_stats()
    return render_template("dashboard.html", stats=stats, analytics=analytics)