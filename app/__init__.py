import time

from flask import Flask, redirect, request, session, url_for
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from app.auth.routes import bp as auth_bp
from app.billing.routes import bp as billing_bp
from app.config import Config
from app.dashboard.routes import bp as dashboard_bp
from app.extensions import csrf, db, login_manager
from app.history.routes import bp as history_bp
from app.marketing.routes import bp as marketing_bp
from app.models import (
    GeneratedVideo,
    MediaAsset,
    OAuthState,
    PaymentTransaction,
    PendingSocialAccountSelection,
    PostJob,
    SocialAccount,
    User,
)
from app.scheduler.routes import bp as scheduler_bp
from app.services.scheduler_service import process_due_jobs
from app.settings.routes import bp as settings_bp
from app.social.routes import bp as social_bp
from app.utils.db_bootstrap import run_schema_upgrades
from app.video.routes import bp as video_bp


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        db.create_all()
        run_schema_upgrades()

    register_blueprints(app)
    register_hooks(app)
    register_context(app)
    return app


def register_blueprints(app):
    app.register_blueprint(marketing_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(settings_bp)


def register_hooks(app):
    @app.before_request
    def process_scheduler_queue():
        if not current_user.is_authenticated:
            return None

        now = time.time()
        last_poll = session.get("_scheduler_last_poll", 0)
        if now - last_poll >= app.config["SCHEDULER_POLL_INTERVAL_SECONDS"]:
            process_due_jobs()
            session["_scheduler_last_poll"] = now
        return None

    @app.before_request
    def redirect_logged_in_users():
        public_endpoints = {
            "marketing.landing",
            "marketing.pricing",
            "marketing.privacy",
            "marketing.terms",
            "auth.login",
            "auth.signup",
            "auth.forgot_password",
        }
        if current_user.is_authenticated and request.endpoint in {"marketing.landing"}:
            return redirect(url_for("dashboard.index"))
        if current_user.is_anonymous and request.endpoint in {"dashboard.root"}:
            return redirect(url_for("auth.login"))
        if current_user.is_authenticated and request.endpoint in public_endpoints and request.path.startswith("/app"):
            return redirect(url_for("dashboard.index"))
        return None


def register_context(app):
    @app.context_processor
    def inject_globals():
        return {
            "brand_name": "VidSnapAI",
            "plan_badges": {
                "free": "Free",
                "lifetime": "Lifetime",
            },
            "current_year": time.gmtime().tm_year,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)
