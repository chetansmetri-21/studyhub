import os
import uuid

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required, current_user

from werkzeug.utils import secure_filename

from app import db
from app.utils.s3_storage import (
    upload_file,
    object_exists,
    generate_presigned_url,
    delete_object
)
from app.models import User, Note, PYQ
from app.utils.upload_security import (
    validate_profile_image
)

from sqlalchemy import text


student = Blueprint("student", __name__)


# =========================================================
# PROFILE PHOTO CONFIGURATION
# =========================================================

PROFILE_ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

MAX_PROFILE_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB


def allowed_profile_image(filename):
    """
    Check whether the uploaded profile image
    uses an allowed file extension.
    """

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in PROFILE_ALLOWED_EXTENSIONS
    )

# =========================================================
# DASHBOARD 
# =========================================================

@student.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html",
        user=current_user
    )


# =========================================================
# PROFILE PHOTO HELPER
# =========================================================

def get_profile_photo_url(user):
    """
    Return a temporary private S3 URL for the user's profile photo.
    Keeps backward compatibility with old local /static/ photos.
    """

    if not user.profile_photo:
        return None

    # Old local profile photo
    if user.profile_photo.startswith("/static/"):
        return user.profile_photo

    # New private S3 profile photo
    try:
        if object_exists(user.profile_photo):
            return generate_presigned_url(
                user.profile_photo,
                download=False,
                expires=900
            )
    except Exception as exc:
        print(
            "[StudyHub Profile Photo URL Error] "
            f"{exc}"
        )

    return None


# =========================================================
# PROFILE
# =========================================================

@student.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    # =====================================================
    # UPDATE PROFILE
    # =====================================================

    if request.method == "POST":

        # =================================================
        # PROFILE PHOTO — PRIVATE AWS S3
        # =================================================

        profile_file = request.files.get("profile_photo")

        if profile_file and profile_file.filename:

            # ---------------------------------------------
            # SECURE IMAGE VALIDATION
            # ---------------------------------------------

            valid_image, image_error = validate_profile_image(
                profile_file
            )

            if not valid_image:
                flash(
                    image_error,
                    "danger"
                )
                return redirect(
                    url_for("student.profile")
                )

            # ---------------------------------------------
            # FILE TYPE VALIDATION
            # ---------------------------------------------

            if not allowed_profile_image(
                profile_file.filename
            ):
                flash(
                    "Please upload a PNG, JPG, JPEG or WEBP image.",
                    "danger"
                )
                return redirect(
                    url_for("student.profile")
                )

            # ---------------------------------------------
            # FILE SIZE VALIDATION
            # ---------------------------------------------

            profile_file.seek(
                0,
                os.SEEK_END
            )

            file_size = profile_file.tell()

            profile_file.seek(0)

            if file_size > MAX_PROFILE_IMAGE_SIZE:
                flash(
                    "Profile photo must be smaller than 2 MB.",
                    "danger"
                )
                return redirect(
                    url_for("student.profile")
                )

            # ---------------------------------------------
            # SECURE UNIQUE FILE NAME
            # ---------------------------------------------

            safe_filename = secure_filename(
                profile_file.filename
            )

            if (
                not safe_filename
                or "." not in safe_filename
            ):
                flash(
                    "Invalid profile image.",
                    "danger"
                )
                return redirect(
                    url_for("student.profile")
                )

            extension = (
                safe_filename
                .rsplit(".", 1)[1]
                .lower()
            )

            filename = (
                f"user_{current_user.id}_"
                f"{uuid.uuid4().hex}."
                f"{extension}"
            )

            # ---------------------------------------------
            # S3 OBJECT KEY
            # ---------------------------------------------

            s3_key = (
                f"profiles/"
                f"{current_user.id}/"
                f"{filename}"
            )

            # ---------------------------------------------
            # UPLOAD TO PRIVATE S3
            # ---------------------------------------------

            import mimetypes

            content_type = (
                mimetypes.guess_type(
                    filename
                )[0]
                or "application/octet-stream"
            )

            try:

                profile_file.seek(0)

                upload_file(
                    file_obj=profile_file,
                    object_key=s3_key,
                    content_type=content_type,
                    metadata={
                        "uploaded_by": str(
                            current_user.id
                        ),
                        "resource_type": "profile_photo"
                    }
                )

            except Exception as exc:

                print(
                    "[StudyHub Profile S3 Upload Error] "
                    f"{exc}"
                )

                flash(
                    "Unable to upload your profile photo.",
                    "danger"
                )

                return redirect(
                    url_for("student.profile")
                )

            # ---------------------------------------------
            # DELETE OLD S3 PROFILE PHOTO
            # ---------------------------------------------

            old_photo = current_user.profile_photo

            if old_photo:

                old_s3_key = None

                # New S3 format:
                # profiles/<user_id>/<filename>
                if old_photo.startswith(
                    "profiles/"
                ):
                    old_s3_key = old_photo

                # Backward compatibility:
                # if database contains an old S3 URL/path
                elif "/profiles/" in old_photo:

                    old_s3_key = (
                        old_photo.split(
                            "/profiles/",
                            1
                        )[1]
                    )

                    old_s3_key = (
                        f"profiles/{old_s3_key}"
                    )

                if old_s3_key:
                    try:
                        if object_exists(old_s3_key):
                            delete_object(
                                old_s3_key
                            )
                    except Exception as exc:
                        print(
                            "[StudyHub Old Profile Photo "
                            f"Cleanup Warning] {exc}"
                        )

            # ---------------------------------------------
            # STORE S3 KEY IN DATABASE
            # ---------------------------------------------

            current_user.profile_photo = s3_key


        # =================================================
        # BASIC EDUCATION
        # =================================================

        current_user.education_level = (
            request.form.get(
                "education_level",
                ""
            ).strip()
            or None
        )

        current_user.course = (
            request.form.get(
                "course",
                ""
            ).strip()
            or None
        )

        current_user.semester = (
            request.form.get(
                "semester",
                ""
            ).strip()
            or None
        )


        # =================================================
        # PREMIUM PROFILE INFORMATION
        # =================================================

        current_user.bio = (
            request.form.get(
                "bio",
                ""
            ).strip()
            or None
        )

        current_user.skills = (
            request.form.get(
                "skills",
                ""
            ).strip()
            or None
        )

        current_user.interests = (
            request.form.get(
                "interests",
                ""
            ).strip()
            or None
        )

        current_user.phone = (
            request.form.get(
                "phone",
                ""
            ).strip()
            or None
        )

        current_user.location = (
            request.form.get(
                "location",
                ""
            ).strip()
            or None
        )


        # =================================================
        # PROFESSIONAL LINKS
        # =================================================

        current_user.linkedin_url = (
            request.form.get(
                "linkedin_url",
                ""
            ).strip()
            or None
        )

        current_user.github_url = (
            request.form.get(
                "github_url",
                ""
            ).strip()
            or None
        )


        # =================================================
        # PROFILE UPDATED TIMESTAMP
        # =================================================

        current_user.profile_updated_at = (
            db.func.current_timestamp()
        )


        # =================================================
        # SAVE DATABASE CHANGES
        # =================================================

        db.session.commit()


        flash(
            "Your profile has been updated successfully.",
            "success"
        )


        return redirect(
            url_for("student.profile")
        )


    # =====================================================
    # PROFILE COMPLETION
    # =====================================================

    profile_fields = [

        current_user.name,

        current_user.email,

        current_user.education_level,

        current_user.course,

        current_user.semester,

        current_user.bio,

        current_user.skills,

        current_user.interests,

        current_user.phone,

        current_user.location,

        current_user.linkedin_url,

        current_user.github_url,

        current_user.profile_photo
    ]


    completed_fields = sum(
        1
        for field in profile_fields
        if field and str(field).strip()
    )


    total_fields = len(
        profile_fields
    )


    profile_completion = (
        round(
            (
                completed_fields
                /
                total_fields
            ) * 100
        )
        if total_fields
        else 0
    )


    # =====================================================
    # USER RESOURCE STATISTICS
    # =====================================================

    uploaded_notes = Note.query.filter(
        Note.uploaded_by == current_user.id
    ).count()


    uploaded_pyqs = PYQ.query.filter(
        PYQ.uploaded_by == current_user.id
    ).count()


    # =====================================================
    # SAVED RESOURCES
    # =====================================================

    try:

        saved_resources = db.session.execute(

            text("""
                SELECT COUNT(*)
                FROM studyhub_bookmarks
                WHERE user_id = :user_id
            """),

            {
                "user_id": current_user.id
            }

        ).scalar() or 0

    except Exception:

        saved_resources = 0


    # =====================================================
    # ACTIVITY SUMMARY
    # =====================================================

    try:

        total_activity = db.session.execute(

            text("""
                SELECT COUNT(*)
                FROM studyhub_activity
                WHERE user_id = :user_id
            """),

            {
                "user_id": current_user.id
            }

        ).scalar() or 0

    except Exception:

        total_activity = 0


    # =====================================================
    # RENDER PROFILE
    # =====================================================

    profile_photo_url = get_profile_photo_url(current_user)

    return render_template(

        "profile.html",

        user=current_user,

        profile_completion=profile_completion,

        uploaded_notes=uploaded_notes,

        uploaded_pyqs=uploaded_pyqs,

        saved_resources=saved_resources,

        total_activity=total_activity,

        profile_photo_url=profile_photo_url
    )