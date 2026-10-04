import re
import secrets
from app import db, limiter

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from flask_login import (
    login_user,
    logout_user,
    current_user,
    login_required
)

from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired
)


from app.models import User


auth = Blueprint("auth", __name__)


# =========================================================
# PASSWORD SECURITY
# =========================================================

MIN_PASSWORD_LENGTH = 10


def validate_password(password):
    """
    Validate password strength.

    Requirements:
    - At least 10 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """

    if not password:
        return False, "Password is required."

    if len(password) < MIN_PASSWORD_LENGTH:
        return False, (
            f"Password must be at least "
            f"{MIN_PASSWORD_LENGTH} characters."
        )

    if not re.search(r"[A-Z]", password):
        return False, (
            "Password must contain at least one uppercase letter."
        )

    if not re.search(r"[a-z]", password):
        return False, (
            "Password must contain at least one lowercase letter."
        )

    if not re.search(r"\d", password):
        return False, (
            "Password must contain at least one number."
        )

    return True, None


# =========================================================
# PASSWORD RESET TOKEN
# =========================================================

def get_serializer():

    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"]
    )


def generate_reset_token(email):

    serializer = get_serializer()

    return serializer.dumps(
        email,
        salt="studyhub-password-reset"
    )


def verify_reset_token(token):

    serializer = get_serializer()

    try:

        email = serializer.loads(
            token,
            salt="studyhub-password-reset",
            max_age=current_app.config.get(
                "PASSWORD_RESET_TOKEN_MAX_AGE",
                1800
            )
        )

        return email

    except (
        SignatureExpired,
        BadSignature
    ):

        return None


# =========================================================
# REGISTER
# =========================================================

@auth.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def register():

    if current_user.is_authenticated:
        return redirect(
            url_for("student.dashboard")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if len(name) > 100:

            flash(
                "Name is too long.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        # -------------------------------------------------
        # EMAIL VALIDATION
        # -------------------------------------------------

        email_pattern = (
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        )

        if not re.match(
            email_pattern,
            email
        ):

            flash(
                "Please enter a valid email address.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if len(email) > 120:

            flash(
                "Email address is too long.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        # -------------------------------------------------
        # PASSWORD VALIDATION
        # -------------------------------------------------

        password_valid, password_error = (
            validate_password(password)
        )

        if not password_valid:

            flash(
                password_error,
                "danger"
            )

            return render_template(
                "register.html"
            )

        # -------------------------------------------------
        # CHECK EXISTING USER
        # -------------------------------------------------

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "An account with this email already exists.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        # -------------------------------------------------
        # CREATE USER
        # -------------------------------------------------

        password_hash = generate_password_hash(
            password
        )

        user = User(
            name=name,
            email=email,
            password_hash=password_hash
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():

    if current_user.is_authenticated:
        return redirect(
            url_for("student.dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        user = User.query.filter_by(
            email=email
        ).first()

        # -------------------------------------------------
        # GENERIC ERROR MESSAGE
        # -------------------------------------------------

        if not user or not check_password_hash(
            user.password_hash,
            password
        ):

            flash(
                "Invalid email or password.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        # -------------------------------------------------
        # CLEAR OLD SESSION DATA
        # -------------------------------------------------

        session.clear()

        # -------------------------------------------------
        # LOGIN
        # -------------------------------------------------

        login_user(
            user,
            remember=False
        )

        # -------------------------------------------------
        # SAFE NEXT URL
        # -------------------------------------------------

        next_url = request.args.get(
            "next",
            ""
        )

        if (
            next_url
            and next_url.startswith("/")
            and not next_url.startswith("//")
        ):
            return redirect(next_url)

        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@auth.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per 10 minutes")
def forgot_password():

    if current_user.is_authenticated:
        return redirect(
            url_for("student.dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        # -------------------------------------------------
        # ALWAYS SHOW SAME RESPONSE
        # -------------------------------------------------

        user = User.query.filter_by(
            email=email
        ).first()

        if user:
            token = generate_reset_token(user.email)

            reset_url = url_for(
                "auth.reset_password",
                token=token,
                _external=True
            )

            # In production, send reset_url through the configured
            # email provider instead of logging the token.
            current_app.logger.info(
                "Password reset requested."
            )

            

        return render_template(
            "forgot_password_sent.html"
        )

    return render_template(
        "forgot_password.html"
    )


# =========================================================
# RESET PASSWORD
# =========================================================

@auth.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes")
def reset_password(token):

    email = verify_reset_token(
        token
    )

    if not email:

        flash(
            "This password reset link is invalid or has expired.",
            "danger"
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    user = User.query.filter_by(
        email=email
    ).first()

    if not user:

        flash(
            "Invalid password reset request.",
            "danger"
        )

        return redirect(
            url_for("auth.forgot_password")
        )

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not password or not confirm_password:

            flash(
                "Please enter both password fields.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        password_valid, password_error = (
            validate_password(password)
        )

        if not password_valid:

            flash(
                password_error,
                "danger"
            )

            return render_template(
                "reset_password.html"
            )

        # -------------------------------------------------
        # UPDATE PASSWORD
        # -------------------------------------------------

        user.password_hash = generate_password_hash(
            password
        )

        db.session.commit()

        flash(
            "Password updated successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "reset_password.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )