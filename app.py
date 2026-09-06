from flask import Flask, request

from config import Config
from database import init_app as init_database
import models

from routes.campaigns import campaigns_bp
from routes.contacts import contacts_bp
from routes.dashboard import dashboard_bp
from routes.templates import templates_bp
from routes.automation import automation_bp
from routes.tracking import tracking_bp
from routes.reports import reports_bp
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_database(app)

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(automation_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(reports_bp)
    @app.before_request
    def run_scheduler():
        if request.endpoint == "static":
            return
        models.process_due_campaigns()

    @app.context_processor
    def inject_helpers():
        return {"to_datetime_local": models.to_datetime_local}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)