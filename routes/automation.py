from flask import Blueprint, render_template

automation_bp = Blueprint("automation", __name__, url_prefix="/automation")


@automation_bp.route("/")
def automation():
    return render_template("automation.html")