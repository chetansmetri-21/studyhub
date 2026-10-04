import os

from dotenv import load_dotenv


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

load_dotenv(
    os.path.join(
        BASE_DIR,
        ".env"
    )
)


class Config:

    # =========================================================
    # SECURITY
    # =========================================================

    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not set. Add it to your .env file."
        )

    # Session cookie security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.getenv(
            "SESSION_COOKIE_SECURE",
            "0"
        ) == "1"
    )

    # Flask-Login remember-me cookie
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    REMEMBER_COOKIE_SECURE = (
        os.getenv(
            "REMEMBER_COOKIE_SECURE",
            os.getenv("SESSION_COOKIE_SECURE", "0")
        ) == "1"
    )

    # Prevent browsers from caching authenticated pages
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # =========================================================
    # DATABASE
    # =========================================================

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(
            BASE_DIR,
            "studyhub.db"
        )
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================================================
    # UPLOADS
    # =========================================================

    # Maximum request/upload size: 50 MB
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    # =========================================================
    # PASSWORD RESET
    # =========================================================

    PASSWORD_RESET_TOKEN_MAX_AGE = int(
        os.getenv(
            "PASSWORD_RESET_TOKEN_MAX_AGE",
            "1800"
        )
    )

    # =========================================================
    # APPLICATION
    # =========================================================

    JSON_SORT_KEYS = False