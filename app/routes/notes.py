import os
import mimetypes

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory
)

from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import text

from app import db, limiter
from app.utils.upload_security import validate_note_file
from app.models import Note, NoteRating, ResourceReport

from app.utils.s3_storage import (
    upload_file,
    object_exists,
    generate_presigned_url,
    delete_object
)


notes = Blueprint("notes", __name__)


# =========================================================
# UPLOAD FOLDER
# =========================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads",
    "notes"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# HELPER
# =========================================================

def get_distinct_values(column):
    """
    Get unique non-empty values from a Note column.
    """

    values = (
        db.session.query(column)
        .filter(
            column.isnot(None),
            column != ""
        )
        .distinct()
        .order_by(column)
        .all()
    )

    return [
        value[0]
        for value in values
    ]


# =========================================================
# AWS S3 FILE HELPERS
# =========================================================

def get_s3_key(note):
    return f"notes/{note.uploaded_by}/{note.file_name}"


def get_local_file_path(note):
    return os.path.join(
        UPLOAD_FOLDER,
        note.file_name
    )


def is_legacy_local_file(note):
    return os.path.isfile(
        get_local_file_path(note)
    )


def get_note_file_url(note, download=False):
    s3_key = get_s3_key(note)

    if object_exists(s3_key):
        return generate_presigned_url(
            s3_key,
            download=download,
            download_name=note.file_name,
            expires=300
        )

    return None


# =========================================================
# NOTES REPOSITORY
# =========================================================

@notes.route("/notes")
@login_required
def notes_list():

    # -----------------------------------------------------
    # FILTER VALUES
    # -----------------------------------------------------

    search = request.args.get(
        "search",
        ""
    ).strip()

    selected_subject = request.args.get(
        "subject",
        ""
    ).strip()

    selected_semester = request.args.get(
        "semester",
        ""
    ).strip()

    selected_education_level = request.args.get(
        "education_level",
        ""
    ).strip()

    selected_course = request.args.get(
        "course",
        ""
    ).strip()


    # -----------------------------------------------------
    # NOTES QUERY
    # -----------------------------------------------------

    query = Note.query.filter(
        Note.verification_status == "approved"
    )


    # Search
    if search:

        search_value = f"%{search}%"

        query = query.filter(
            db.or_(
                Note.title.ilike(search_value),
                Note.description.ilike(search_value),
                Note.subject.ilike(search_value),
                Note.course.ilike(search_value),
                Note.education_level.ilike(search_value),
                Note.semester.ilike(search_value)
            )
        )


    # Education level
    if selected_education_level:

        query = query.filter(
            Note.education_level
            == selected_education_level
        )


    # Course
    if selected_course:

        query = query.filter(
            Note.course
            == selected_course
        )


    # Semester
    if selected_semester:

        query = query.filter(
            Note.semester
            == selected_semester
        )


    # Subject
    if selected_subject:

        query = query.filter(
            Note.subject
            == selected_subject
        )


    # -----------------------------------------------------
    # GET NOTES
    # -----------------------------------------------------

    notes_data = (
        query
        .order_by(
            Note.uploaded_at.desc()
        )
        .all()
    )


    # -----------------------------------------------------
    # RESULT COUNT
    # -----------------------------------------------------

    result_count = len(
        notes_data
    )


    # -----------------------------------------------------
    # FILTER OPTIONS
    # -----------------------------------------------------

    available_education_levels = (
        get_distinct_values(
            Note.education_level
        )
    )

    available_courses = (
        get_distinct_values(
            Note.course
        )
    )

    available_semesters = (
        get_distinct_values(
            Note.semester
        )
    )

    available_subjects = (
        get_distinct_values(
            Note.subject
        )
    )


    # -----------------------------------------------------
    # RATINGS
    # -----------------------------------------------------

    rating_averages = {}
    rating_counts = {}
    user_ratings = {}


    for note in notes_data:

        ratings = (
            NoteRating.query
            .filter_by(
                note_id=note.id
            )
            .all()
        )


        if ratings:

            average = (
                sum(
                    rating.rating
                    for rating in ratings
                )
                / len(ratings)
            )

            rating_averages[note.id] = round(
                average,
                1
            )

            rating_counts[note.id] = len(
                ratings
            )

        else:

            rating_averages[note.id] = 0
            rating_counts[note.id] = 0


        current_rating = (
            NoteRating.query
            .filter_by(
                note_id=note.id,
                user_id=current_user.id
            )
            .first()
        )


        if current_rating:

            user_ratings[note.id] = (
                current_rating.rating
            )


    # -----------------------------------------------------
    # RECOMMENDED NOTES
    # -----------------------------------------------------

    recommended_notes = []


    if current_user.education_level:

        recommended_query = Note.query.filter(
            Note.education_level
            == current_user.education_level
        )


        if current_user.course:

            recommended_query = (
                recommended_query.filter(
                    db.or_(
                        Note.course
                        == current_user.course,

                        Note.course.is_(None),

                        Note.course == ""
                    )
                )
            )


        if current_user.semester:

            recommended_query = (
                recommended_query.filter(
                    db.or_(
                        Note.semester
                        == current_user.semester,

                        Note.semester.is_(None),

                        Note.semester == ""
                    )
                )
            )


        recommended_notes = (
            recommended_query
            .order_by(
                Note.uploaded_at.desc()
            )
            .limit(6)
            .all()
        )


    # -----------------------------------------------------
    # TRENDING NOTES
    # -----------------------------------------------------

    trending_notes = (
        Note.query
        .order_by(
            Note.views.desc(),
            Note.downloads.desc()
        )
        .limit(6)
        .all()
    )


    # -----------------------------------------------------
    # RENDER
    # -----------------------------------------------------

    return render_template(
        "notes.html",

        # Notes
        notes=notes_data,

        # Search/filter values
        search=search,
        selected_subject=selected_subject,
        selected_semester=selected_semester,
        selected_education_level=(
            selected_education_level
        ),
        selected_course=selected_course,

        # Dynamic filter options
        available_education_levels=(
            available_education_levels
        ),
        available_courses=(
            available_courses
        ),
        available_semesters=(
            available_semesters
        ),
        available_subjects=(
            available_subjects
        ),

        # Results
        result_count=result_count,

        # Ratings
        rating_averages=rating_averages,
        rating_counts=rating_counts,
        user_ratings=user_ratings,

        # Other sections
        recommended_notes=recommended_notes,
        trending_notes=trending_notes,

        # Upload section
        upload=False
    )


# =========================================================
# UPLOAD PAGE
# =========================================================

@notes.route(
    "/notes/upload",
    methods=["GET"]
)
@login_required
@limiter.limit("10 per hour")
def upload_page():

    return render_template(
        "notes.html",

        notes=[],

        search="",
        selected_subject="",
        selected_semester="",
        selected_education_level="",
        selected_course="",

        available_education_levels=(
            get_distinct_values(
                Note.education_level
            )
        ),

        available_courses=(
            get_distinct_values(
                Note.course
            )
        ),

        available_semesters=(
            get_distinct_values(
                Note.semester
            )
        ),

        available_subjects=(
            get_distinct_values(
                Note.subject
            )
        ),

        result_count=0,

        rating_averages={},
        rating_counts={},
        user_ratings={},

        recommended_notes=[],
        trending_notes=[],

        upload=True
    )


# =========================================================
# UPLOAD NOTE
# =========================================================

@notes.route(
    "/notes/upload",
    methods=["POST"]
)
@login_required
def upload_note():

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    education_level = request.form.get(
        "education_level",
        ""
    ).strip()

    course = request.form.get(
        "course",
        ""
    ).strip()

    semester = request.form.get(
        "semester",
        ""
    ).strip()

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    file = request.files.get(
        "file"
    )


    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not title:

        flash(
            "Please enter a note title."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    if not education_level:

        flash(
            "Please select an education level."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    if not course:

        flash(
            "Please enter the course or stream."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    if not semester:

        flash(
            "Please enter the semester, year or class."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    if not subject:

        flash(
            "Please enter the subject."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    if not file or not file.filename:

        flash(
            "Please select a study material file."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    # -----------------------------------------------------
    # FILE NAME
    # -----------------------------------------------------

    filename = secure_filename(
        file.filename
    )


    if not filename:

        flash(
            "Invalid file name."
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    # -----------------------------------------------------
    # SECURE FILE VALIDATION
    # -----------------------------------------------------

    valid_file, file_error = validate_note_file(
        file
    )

    if not valid_file:

        flash(
            file_error,
            "danger"
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )

    

    # -----------------------------------------------------
    # PREVENT DUPLICATE FILE NAME IN S3
    # -----------------------------------------------------

    base_name, file_extension = (
        os.path.splitext(filename)
    )

    final_filename = filename

    counter = 1

    while True:

        s3_key = (
            f"notes/"
            f"{current_user.id}/"
            f"{final_filename}"
        )

        if not object_exists(s3_key):
            break

        final_filename = (
            f"{base_name}_{counter}"
            f"{file_extension}"
        )

        counter += 1


    # -----------------------------------------------------
    # UPLOAD FILE TO AWS S3
    # -----------------------------------------------------

    import mimetypes

    content_type = (
        mimetypes.guess_type(
            final_filename
        )[0]
        or "application/octet-stream"
    )

    s3_key = (
        f"notes/"
        f"{current_user.id}/"
        f"{final_filename}"
    )

    try:

        upload_file(
            file_obj=file,
            object_key=s3_key,
            content_type=content_type,
            metadata={
                "uploaded_by": str(
                    current_user.id
                ),
                "education_level": education_level,
                "course": course,
                "semester": semester,
                "subject": subject
            }
        )

    except Exception as exc:

        print(
            f"[StudyHub S3 Upload Error] {exc}"
        )

        flash(
            "Unable to upload the file to cloud storage.",
            "danger"
        )

        return redirect(
            url_for(
                "notes.upload_page"
            )
        )


    # -----------------------------------------------------
    # CREATE DATABASE RECORD
    # -----------------------------------------------------

    note = Note(
        title=title,
        description=description,
        education_level=education_level,
        course=course,
        semester=semester,
        subject=subject,
        file_name=final_filename,
        uploaded_by=current_user.id,
        views=0,
        downloads=0,
        rating=0,
        verification_status="approved"
    )

    db.session.add(
        note
    )

    db.session.commit()


    flash(
        "Note uploaded successfully!"
    )


    return redirect(
        url_for(
            "notes.notes_list"
        )
    )


# =========================================================
# VIEW NOTE DETAILS
# =========================================================

@notes.route("/notes/view/<int:note_id>")
@login_required
def view_note(note_id):
    note = Note.query.get_or_404(note_id)

    # -----------------------------------------------------
    # CHECK AWS S3 FIRST
    # -----------------------------------------------------

    s3_key = get_s3_key(note)

    if object_exists(s3_key):
        note.views = (note.views or 0) + 1

        # -----------------------------------------------------
        # RECORD STUDYHUB ACTIVITY
        # -----------------------------------------------------

        db.session.execute(
            text("""
                INSERT INTO studyhub_activity
                (
                    user_id,
                    resource_type,
                    resource_id,
                    action
                )
                VALUES
                (
                    :user_id,
                    'note',
                    :resource_id,
                    'viewed'
                )
            """),
            {
                "user_id": current_user.id,
                "resource_id": note.id
            }
        )

        db.session.commit()

        file_url = generate_presigned_url(
            s3_key,
            download=False,
            download_name=note.file_name,
            expires=300
        )

        if file_url:
            return redirect(file_url)

    # -----------------------------------------------------
    # LEGACY LOCAL FILE FALLBACK
    # -----------------------------------------------------

    if is_legacy_local_file(note):
        note.views = (note.views or 0) + 1

        # -----------------------------------------------------
        # RECORD STUDYHUB ACTIVITY
        # -----------------------------------------------------

        db.session.execute(
            text("""
                INSERT INTO studyhub_activity
                (
                    user_id,
                    resource_type,
                    resource_id,
                    action
                )
                VALUES
                (
                    :user_id,
                    'note',
                    :resource_id,
                    'viewed'
                )
            """),
            {
                "user_id": current_user.id,
                "resource_id": note.id
            }
        )

        db.session.commit()

        return send_from_directory(
            UPLOAD_FOLDER,
            note.file_name
        )

        return send_from_directory(
            UPLOAD_FOLDER,
            note.file_name
        )

    flash(
        "The file for this note is no longer available.",
        "warning"
    )

    return redirect(
        url_for(
            "notes.notes_list"
        )
    )


# =========================================================
# REPORT NOTE
# =========================================================

@notes.route(
    "/notes/<int:note_id>/report",
    methods=["POST"]
)
@login_required
def report_note(note_id):

    note = Note.query.get_or_404(note_id)

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if not reason:

        flash(
            "Please select a reason for reporting this note.",
            "warning"
        )

        return redirect(
            url_for(
                "notes.notes_list"
            )
        )

    report = ResourceReport(

        user_id=current_user.id,

        resource_type="note",

        resource_id=note.id,

        reason=reason,

        description=description or None,

        status="pending"

    )

    db.session.add(report)

    db.session.commit()

    flash(
        "Thank you. Your report has been submitted for review.",
        "success"
    )

    return redirect(
        url_for(
            "notes.notes_list"
        )
    )

# =========================================================
# OPEN NOTE FILE
# =========================================================

@notes.route(
    "/notes/file/<int:note_id>"
)
@login_required
def open_note_file(note_id):

    note = Note.query.get_or_404(
        note_id
    )

    # -----------------------------------------------------
    # TRY AWS S3 FIRST
    # -----------------------------------------------------

    s3_key = get_s3_key(note)

    if object_exists(s3_key):

        file_url = generate_presigned_url(
            s3_key,
            download=False,
            download_name=note.file_name,
            expires=300
        )

        if file_url:
            return redirect(file_url)

    # -----------------------------------------------------
    # LEGACY LOCAL FILE FALLBACK
    # -----------------------------------------------------

    file_path = get_local_file_path(note)

    if is_legacy_local_file(note):

        return send_from_directory(
            UPLOAD_FOLDER,
            note.file_name
        )

    # -----------------------------------------------------
    # FILE NOT FOUND
    # -----------------------------------------------------

    flash(
        "The file for this note is no longer available.",
        "warning"
    )

    return redirect(
        url_for(
            "notes.notes_list"
        )
    )
# =========================================================
# DOWNLOAD NOTE
# =========================================================

@notes.route(
    "/notes/download/<int:note_id>"
)
@login_required
def download_note(note_id):

    note = Note.query.get_or_404(
        note_id
    )

    # -----------------------------------------------------
    # TRY AWS S3 FIRST
    # -----------------------------------------------------

    s3_key = get_s3_key(note)

    if object_exists(s3_key):

        file_url = generate_presigned_url(
            s3_key,
            download=True,
            download_name=note.file_name,
            expires=300
        )

        if file_url:

            note.downloads = (
                note.downloads or 0
            ) + 1

            # -----------------------------------------------------
            # RECORD STUDYHUB DOWNLOAD ACTIVITY
            # -----------------------------------------------------

            db.session.execute(
                text("""
                    INSERT INTO studyhub_activity
                    (
                        user_id,
                        resource_type,
                        resource_id,
                        action
                    )
                    VALUES
                    (
                        :user_id,
                        'note',
                        :resource_id,
                        'downloaded'
                    )
                """),
                {
                    "user_id": current_user.id,
                    "resource_id": note.id
                }
            )

            db.session.commit()

            return redirect(file_url)

    # -----------------------------------------------------
    # LEGACY LOCAL FILE FALLBACK
    # -----------------------------------------------------

    if is_legacy_local_file(note):

        note.downloads = (
            note.downloads or 0
        ) + 1

        # -----------------------------------------------------
        # RECORD STUDYHUB DOWNLOAD ACTIVITY
        # -----------------------------------------------------

        db.session.execute(
            text("""
                INSERT INTO studyhub_activity
                (
                    user_id,
                    resource_type,
                    resource_id,
                    action
                )
                VALUES
                (
                    :user_id,
                    'note',
                    :resource_id,
                    'downloaded'
                )
            """),
            {
                "user_id": current_user.id,
                "resource_id": note.id
            }
        )

        db.session.commit()

        return send_from_directory(
            UPLOAD_FOLDER,
            note.file_name,
            as_attachment=True
        )

    # -----------------------------------------------------
    # FILE NOT FOUND
    # -----------------------------------------------------

    flash(
        "The file for this note is no longer available.",
        "warning"
    )

    return redirect(
        url_for(
            "notes.notes_list"
        )
    )

# =========================================================
# RATE NOTE
# =========================================================

@notes.route(
    "/notes/rate/<int:note_id>",
    methods=["POST"]
)
@login_required
def rate_note(note_id):

    note = Note.query.get_or_404(
        note_id
    )


    try:

        rating_value = int(
            request.form.get(
                "rating",
                0
            )
        )

    except ValueError:

        flash(
            "Invalid rating."
        )

        return redirect(
            url_for(
                "notes.notes_list"
            )
        )


    if rating_value < 1 or rating_value > 5:

        flash(
            "Rating must be between 1 and 5."
        )

        return redirect(
            url_for(
                "notes.notes_list"
            )
        )


    existing_rating = (
        NoteRating.query
        .filter_by(
            note_id=note.id,
            user_id=current_user.id
        )
        .first()
    )


    if existing_rating:

        existing_rating.rating = (
            rating_value
        )

    else:

        new_rating = NoteRating(

            note_id=note.id,

            user_id=current_user.id,

            rating=rating_value
        )

        db.session.add(
            new_rating
        )


    db.session.commit()


    # -----------------------------------------------------
    # UPDATE NOTE AVERAGE
    # -----------------------------------------------------

    ratings = (
        NoteRating.query
        .filter_by(
            note_id=note.id
        )
        .all()
    )


    if ratings:

        note.rating = (
            sum(
                rating.rating
                for rating in ratings
            )
            / len(ratings)
        )

    else:

        note.rating = 0


    db.session.commit()


    flash(
        "Your rating has been saved."
    )


    return redirect(
        url_for(
            "notes.notes_list"
        )
    )

