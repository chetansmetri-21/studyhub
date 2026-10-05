import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask import Flask, render_template, request
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.getenv(
        "RATELIMIT_STORAGE_URI",
        "memory://"
    ),
)


def create_app():

    app = Flask(__name__)

    app.config.from_object("config.Config")

    # Initialize extensions
    db.init_app(app)

    login_manager.init_app(app)
    csrf.init_app(app)

    limiter.init_app(app)

    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    # =====================================================
    # ROUTES
    # =====================================================

    from app.routes.enhancements import enhancements
    app.register_blueprint(enhancements)

    from app.routes.auth import auth
    app.register_blueprint(auth)

    from app.routes.student import student
    app.register_blueprint(student)

    from app.routes.notes import notes
    app.register_blueprint(notes)

    from app.routes.pyq import pyq
    app.register_blueprint(pyq)

    from app.routes.search import search
    app.register_blueprint(search)

    from app.routes.admin import admin
    app.register_blueprint(admin)

    # StudyHub AI
    from app.routes.ai_assistant import ai_assistant
    app.register_blueprint(ai_assistant)

    # Community
    from app.routes.community import community
    app.register_blueprint(community)

    # Recommendations
    from app.routes.recommendations import recommendations
    app.register_blueprint(recommendations)

    

    # =====================================================
    # HOME
    # =====================================================

    @app.route("/")
    def home():
        return render_template("index.html")

    # =====================================================
    # ERROR HANDLERS
    # =====================================================

    @app.errorhandler(404)
    def page_not_found(error):
        return """
        <html>
        <head><title>404 - Page Not Found</title></head>
        <body>
            <h1>404 - Page Not Found</h1>
            <p>The page you are looking for does not exist.</p>
            <a href="/">Go to StudyHub</a>
        </body>
        </html>
        """, 404


    @app.errorhandler(500)
    def internal_server_error(error):
        return """
        <html>
        <head><title>500 - Internal Server Error</title></head>
        <body>
            <h1>500 - Internal Server Error</h1>
            <p>Something went wrong on the server.</p>
            <a href="/">Go to StudyHub</a>
        </body>
        </html>
        """, 500

    # =====================================================
    # SECURITY HEADERS
    # =====================================================

    @app.after_request
    def add_security_headers(response):

        response.headers["X-Content-Type-Options"] = "nosniff"

        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        response.headers[
            "Referrer-Policy"
        ] = "strict-origin-when-cross-origin"

        response.headers[
            "Permissions-Policy"
        ] = "camera=(), microphone=(), geolocation=()"

        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        response.headers["Cache-Control"] = (
            "no-store"
            if request.method != "GET"
            else response.headers.get(
                "Cache-Control",
                ""
            )
        )

        if os.getenv("SESSION_COOKIE_SECURE", "0") == "1":
            response.headers[
                "Strict-Transport-Security"
            ] = (
                "max-age=31536000; "
                "includeSubDomains"
            )

        return response

    # =====================================================
    # DATABASE INITIALIZATION
    # =====================================================
    @app.route("/health")
    def health_check():
        try:
            db.session.execute(db.text("SELECT 1"))
            return {
                "status": "ok",
                "database": "ok"
            }, 200

        except Exception:
            db.session.rollback()

            return {
                "status": "error",
                "database": "unavailable"
            }, 503

    # =========================================================
    # PRODUCTION ERROR HANDLERS
    # =========================================================

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "errors/404.html"
        ), 404


    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()

        app.logger.exception(
            "Unhandled StudyHub server error"
        )

        return render_template(
            "errors/500.html"
        ), 500

        
    return app