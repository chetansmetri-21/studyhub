from email.mime import text
import os
import json
import hashlib
import pymupdf
import uuid

from app.utils.visual_analyzer import analyze_pdf_visuals

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory
)

from flask_login import (
    login_required,
    current_user
)

from sqlalchemy import text

from werkzeug.utils import secure_filename

from app import db, limiter
from app.models import PYQ, ResourceReport

from app.utils.pdf_extractor import (
    extract_text_from_pdf
)

from app.utils.question_parser import (
    parse_questions
)

from app.utils.visual_analyzer import (
    analyze_pdf_visuals
)

from app.utils.question_analyzer import (
    group_similar_questions,
    get_group_topic
)

from app.utils.storage import (
    save_file,
    get_file_path
)

from app.utils.s3_storage import (
    upload_file,
    object_exists,
    generate_presigned_url
)
from app.utils.upload_security import (
    validate_pdf
)

pyq = Blueprint(
    "pyq",
    __name__,
    url_prefix="/pyq"
)


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".."
    )
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


ALLOWED_EXTENSIONS = {
    "pdf"
}


def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )

# ============================================================
# S3 STORAGE HELPERS
# ============================================================

def get_pyq_s3_key(pyq_item):
    """
    Generate the S3 key for a PYQ.

    New PYQs:
        pyq/<user_id>/<filename>

    Existing local PYQs remain supported through
    the local-file fallback.
    """
    return (
        f"pyq/"
        f"{pyq_item.uploaded_by}/"
        f"{pyq_item.file_name}"
    )


def is_legacy_local_pyq(pyq_item):
    """
    Check whether an older PYQ still exists locally.
    """
    file_path = get_file_path(
        pyq_item.file_name,
        category="pyq"
    )

    return os.path.isfile(file_path)
# ============================================================
# SERVE PYQ VISUAL IMAGES
# ============================================================

@pyq.route("/visual/<path:filename>")
@login_required
def serve_pyq_visual(filename):

    from flask import send_from_directory

    # Serve an existing PNG immediately. If an older PNG is
    # missing, rebuild only that requested PDF page and cache it.
    # This avoids running OCR/PDF analysis when the page loads.

    pyq_folder = os.path.abspath(
        os.path.join(UPLOAD_FOLDER, "pyq")
    )

    safe_filename = os.path.basename(filename)

    shared_folder = os.path.join(
        pyq_folder,
        "visuals"
    )

    os.makedirs(shared_folder, exist_ok=True)

    shared_path = os.path.join(
        shared_folder,
        safe_filename
    )

    if os.path.isfile(shared_path):
        return send_from_directory(
            shared_folder,
            safe_filename
        )

    # Search legacy visual folders.
    for root, dirs, files in os.walk(pyq_folder):
        if safe_filename in files:
            candidate = os.path.abspath(
                os.path.join(root, safe_filename)
            )
            if candidate.startswith(pyq_folder + os.sep):
                return send_from_directory(
                    root,
                    safe_filename
                )

    # Find which PYQ and PDF page this filename belongs to.
    target_paper = None
    target_page = None

    papers_with_visuals = (
        PYQ.query
        .filter(PYQ.verification_status == "approved")
        .all()
    )

    for paper in papers_with_visuals:

        if not paper.visual_analysis:
            continue

        try:
            stored_visuals = json.loads(
                paper.visual_analysis
            )
        except Exception:
            continue

        if not isinstance(stored_visuals, list):
            continue

        for visual in stored_visuals:

            if not isinstance(visual, dict):
                continue

            stored_filename = (
                visual.get("image_filename")
                or ""
            )

            if not stored_filename:
                stored_path = (
                    visual.get("image_path")
                    or ""
                )
                if stored_path:
                    stored_filename = os.path.basename(
                        stored_path
                    )

            if stored_filename != safe_filename:
                continue

            try:
                page_number = int(
                    visual.get("page")
                )
            except (TypeError, ValueError):
                page_number = None

            if page_number and page_number > 0:
                target_paper = paper
                target_page = page_number

            break

        if target_paper is not None:
            break

    if target_paper is None or target_page is None:
        return ("Visual preview not found", 404)

    # Get the locally saved source PDF.
    pdf_path = get_file_path(
        target_paper.file_name,
        category="pyq"
    )

    if not os.path.isfile(pdf_path):
        return (
            "Source PDF not available for visual preview",
            404
        )

    document = None

    try:

        document = pymupdf.open(pdf_path)

        if target_page > len(document):
            return ("Visual page does not exist", 404)

        page = document[target_page - 1]

        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(1.5, 1.5),
            alpha=False
        )

        pixmap.save(shared_path)

    except Exception as exc:

        print(
            "[StudyHub Visual Preview Error] "
            f"{exc}"
        )

        return (
            "Unable to generate visual preview",
            500
        )

    finally:

        if document:
            document.close()

    if os.path.isfile(shared_path):
        return send_from_directory(
            shared_folder,
            safe_filename
        )

    return ("Visual preview not found", 404)


# ============================================================
# PYQ REPOSITORY
# ============================================================

@pyq.route("/")
@login_required
def pyq_repository():

    search = request.args.get(
        "search",
        ""
    ).strip()

    education_level = request.args.get(
        "education_level",
        ""
    ).strip()

    course = request.args.get(
        "course",
        ""
    ).strip()

    semester = request.args.get(
        "semester",
        ""
    ).strip()

    subject = request.args.get(
        "subject",
        ""
    ).strip()

    exam_type = request.args.get(
        "exam_type",
        ""
    ).strip()

    exam_year = request.args.get(
        "exam_year",
        ""
    ).strip()

    exam_session = request.args.get(
        "exam_session",
        ""
    ).strip()

    query = PYQ.query.filter(
        PYQ.verification_status == "approved"
    )

    if search:

        query = query.filter(
            db.or_(
                PYQ.title.ilike(
                    f"%{search}%"
                ),
                PYQ.subject.ilike(
                    f"%{search}%"
                ),
                PYQ.course.ilike(
                    f"%{search}%"
                )
            )
        )

    if education_level:

        query = query.filter(
            PYQ.education_level
            == education_level
        )

    if course:

        query = query.filter(
            PYQ.course
            == course
        )

    if semester:

        query = query.filter(
            PYQ.semester
            == semester
        )

    if subject:

        query = query.filter(
            PYQ.subject
            == subject
        )

    if exam_type:

        query = query.filter(
            PYQ.exam_type
            == exam_type
        )

    if exam_year:

        try:

            query = query.filter(
                PYQ.exam_year
                == int(exam_year)
            )

        except ValueError:
            pass

    if exam_session:

        query = query.filter(
            PYQ.exam_session
            == exam_session
        )

    pyqs = query.order_by(
        PYQ.exam_year.desc(),
        PYQ.id.desc()
    ).all()

    available_education_levels = [
        value[0]
        for value in db.session.query(
            PYQ.education_level
        )
        .filter(
            PYQ.education_level.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.education_level
        )
        .all()
        if value[0]
    ]

    available_courses = [
        value[0]
        for value in db.session.query(
            PYQ.course
        )
        .filter(
            PYQ.course.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.course
        )
        .all()
        if value[0]
    ]

    available_semesters = [
        value[0]
        for value in db.session.query(
            PYQ.semester
        )
        .filter(
            PYQ.semester.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.semester
        )
        .all()
        if value[0]
    ]

    available_subjects = [
        value[0]
        for value in db.session.query(
            PYQ.subject
        )
        .filter(
            PYQ.subject.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.subject
        )
        .all()
        if value[0]
    ]

    available_exam_types = [
        value[0]
        for value in db.session.query(
            PYQ.exam_type
        )
        .filter(
            PYQ.exam_type.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.exam_type
        )
        .all()
        if value[0]
    ]

    available_exam_years = [
        value[0]
        for value in db.session.query(
            PYQ.exam_year
        )
        .filter(
            PYQ.exam_year.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.exam_year.desc()
        )
        .all()
        if value[0]
    ]

    available_exam_sessions = [
        value[0]
        for value in db.session.query(
            PYQ.exam_session
        )
        .filter(
            PYQ.exam_session.isnot(None)
        )
        .distinct()
        .order_by(
            PYQ.exam_session
        )
        .all()
        if value[0]
    ]

    return render_template(
        "pyq.html",
        pyqs=pyqs,
        search=search,
        education_level=education_level,
        course=course,
        semester=semester,
        subject=subject,
        exam_type=exam_type,
        exam_year=exam_year,
        exam_session=exam_session,
        available_education_levels=available_education_levels,
        available_courses=available_courses,
        available_semesters=available_semesters,
        available_subjects=available_subjects,
        available_exam_types=available_exam_types,
        available_exam_years=available_exam_years,
        available_exam_sessions=available_exam_sessions
    )


# ============================================================
# UPLOAD PYQ
# ============================================================

@pyq.route("/upload", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per hour", methods=["POST"])
def upload_pyq():

    # =========================================================
    # POST — PROCESS UPLOAD
    # =========================================================
    if request.method == "POST":

        title = request.form.get("title", "").strip()

        education_level = request.form.get(
            "education_level", ""
        ).strip()

        course = request.form.get(
            "course", ""
        ).strip()

        semester = request.form.get(
            "semester", ""
        ).strip()

        subject = request.form.get(
            "subject", ""
        ).strip()

        custom_subject = request.form.get(
            "custom_subject", ""
        ).strip()

        # Custom subject
        if subject == "Other / My Subject" and custom_subject:
            subject = custom_subject

        exam_type = request.form.get(
            "exam_type", ""
        ).strip()

        exam_year = request.form.get(
            "exam_year", ""
        ).strip()

        exam_session = request.form.get(
            "exam_session", ""
        ).strip()

        file = request.files.get("file")

        # -----------------------------------------------------
        # BASIC VALIDATION
        # -----------------------------------------------------

        if not title:
            flash("Please enter a title.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        if not education_level:
            flash("Please select an education level.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        if not course:
            flash("Please select or enter a course.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        if not subject:
            flash("Please select or enter a subject.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        if not exam_year:
            flash("Please enter the exam year.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        try:
            exam_year_int = int(exam_year)
        except ValueError:
            flash("Exam year must be a valid number.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        if not file or not file.filename:
            flash("Please select a PDF file.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        # -----------------------------------------------------
        # SECURE PDF VALIDATION
        # -----------------------------------------------------

        valid_pdf, pdf_error = validate_pdf(
            file
        )

        if not valid_pdf:

            flash(
                pdf_error,
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "danger")
            return redirect(url_for("pyq.upload_pyq"))

        # -----------------------------------------------------
        # PDF VALIDATION
        # -----------------------------------------------------

        try:
            file.stream.seek(0)

            header = file.stream.read(5)

            file.stream.seek(0)

            if header != b"%PDF-":
                flash(
                    "The uploaded file does not appear to be a valid PDF.",
                    "danger"
                )
                return redirect(
                    url_for("pyq.upload_pyq")
                )

        except Exception as exc:
            print(
                f"[StudyHub PDF Validation Error] {exc}"
            )

            flash(
                "Unable to process the uploaded PDF.",
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # -----------------------------------------------------
        # CALCULATE FILE HASH
        # -----------------------------------------------------

        try:
            file.stream.seek(0)

            file_bytes = file.read()

            file.stream.seek(0)

            file_hash = hashlib.sha256(
                file_bytes
            ).hexdigest()

        except Exception as exc:
            print(
                f"[StudyHub File Hash Error] {exc}"
            )

            flash(
                "Unable to process the uploaded PDF.",
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # -----------------------------------------------------
        # DUPLICATE FILE CHECK
        # -----------------------------------------------------

        existing_file = PYQ.query.filter_by(
            file_hash=file_hash
        ).first()

        if existing_file:

            flash(
                "This exact PDF has already been uploaded to StudyHub.",
                "warning"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # -----------------------------------------------------
        # DUPLICATE RESOURCE CHECK
        # -----------------------------------------------------

        existing_pyq = PYQ.query.filter(
            PYQ.uploaded_by == current_user.id,
            PYQ.title == title,
            PYQ.course == course,
            PYQ.subject == subject,
            PYQ.exam_year == exam_year_int,
            PYQ.exam_session == (
                exam_session
                if exam_session
                else None
            )
        ).first()

        if existing_pyq:

            flash(
                "A PYQ with the same title, course, subject, "
                "exam year and exam session already exists.",
                "warning"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # -----------------------------------------------------
        # SAFE FILE NAME
        # -----------------------------------------------------

        original_filename = secure_filename(
            file.filename
        )

        if not original_filename:

            flash(
                "Invalid file name.",
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        filename = (
            f"user_{current_user.id}_"
            f"{uuid.uuid4().hex}.pdf"
        )

        # =====================================================
        # 1. SAVE LOCAL COPY FIRST
        # =====================================================

        try:

            file.stream.seek(0)

            saved_filename = save_file(
                file,
                filename,
                category="pyq"
            )

            file_path = get_file_path(
                saved_filename,
                category="pyq"
            )

            if not os.path.isfile(file_path):
                raise FileNotFoundError(
                    f"Saved PYQ file not found: {file_path}"
                )
            
        except Exception as exc:

            print(
                f"[StudyHub Local Save Error] {exc}"
            )

            flash(
                "Unable to save the uploaded PDF.",
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # =====================================================
        # 2. UPLOAD LOCAL COPY TO AWS S3
        # =====================================================

        import mimetypes

        s3_key = (
            f"pyq/"
            f"{current_user.id}/"
            f"{saved_filename}"
        )

        content_type = (
            mimetypes.guess_type(
                saved_filename
            )[0]
            or "application/pdf"
        )

        try:

            with open(
                file_path,
                "rb"
            ) as local_file:

                upload_file(
                    file_obj=local_file,
                    object_key=s3_key,
                    content_type=content_type,
                    metadata={
                        "uploaded_by": str(
                            current_user.id
                        ),
                        "education_level": education_level,
                        "course": course,
                        "semester": semester,
                        "subject": subject,
                        "exam_year": str(
                            exam_year_int
                        ),
                        "exam_session": (
                            exam_session
                            or ""
                        )
                    }
                )

        except Exception as exc:

            print(
                f"[StudyHub S3 PYQ Upload Error] {exc}"
            )

            flash(
                "Unable to upload the PYQ to cloud storage.",
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # =====================================================
        # 3. EXTRACT PDF TEXT
        # =====================================================

        extracted_text = ""

        try:

            extracted_text = (
                extract_text_from_pdf(
                    file_path
                )
                or ""
            )

        except Exception as exc:

            print(
                f"[StudyHub PDF Extraction Error] {exc}"
            )

        # =====================================================
        # 4. PARSE QUESTIONS
        # =====================================================

        parsed_questions = []
        visual_analysis = []

        if extracted_text.strip():

            # -------------------------------------------------
            # QUESTION PARSING
            # -------------------------------------------------

            try:

                parsed_questions = (
                    parse_questions(
                        extracted_text
                    )
                    or []
                )

            except Exception as exc:

                print(
                    f"[StudyHub Question Parsing Error] {exc}"
                )

                parsed_questions = []

            # -------------------------------------------------
            # VISUAL / DIAGRAM / TABLE ANALYSIS
            # -------------------------------------------------

            try:

                visual_analysis = (
                    analyze_pdf_visuals(
                        file_path
                    )
                    or []
                )

                print(
                    "[StudyHub Visual Analysis] "
                    f"Detected {len(visual_analysis)} "
                    "visual page(s)."
                )

            except Exception as exc:

                print(
                    "[StudyHub Visual Analysis Error]:",
                    exc
                )

                visual_analysis = []
        # =====================================================
        # 5. CREATE DATABASE RECORD
        # =====================================================

        new_pyq = PYQ(

            title=title,

            education_level=education_level,

            course=course,

            semester=(
                semester
                if semester
                else None
            ),

            subject=subject,

            exam_type=(
                exam_type
                if exam_type
                else None
            ),

            exam_year=exam_year_int,

            exam_session=(
                exam_session
                if exam_session
                else None
            ),

            file_name=saved_filename,

            uploaded_by=current_user.id,

            extracted_text=(
                extracted_text
                if extracted_text
                else None
            ),

            # IMPORTANT:
            # Database column is TEXT,
            # so Python list must be converted to JSON.
            parsed_questions=(
                json.dumps(
                    parsed_questions,
                    ensure_ascii=False
                )
                if parsed_questions
                else None
            ),

            visual_analysis=(
                json.dumps(
                    visual_analysis,
                    ensure_ascii=False
                )
                if visual_analysis
                else None
            ),

            verification_status="approved",

            file_hash=file_hash
        )

        # =====================================================
        # 6. SAVE DATABASE
        # =====================================================

        try:

            db.session.add(
                new_pyq
            )

            db.session.commit()

        except Exception as exc:

            db.session.rollback()

            print(
                f"[StudyHub PYQ Database Error] {exc}"
            )

            flash(
                "Unable to save the PYQ information.",
                "danger"
            )

            return redirect(
                url_for("pyq.upload_pyq")
            )

        # =====================================================
        # SUCCESS
        # =====================================================

        flash(
            "PYQ uploaded successfully.",
            "success"
        )

        return redirect(
            url_for("pyq.pyq_repository")
        )

    # =========================================================
    # GET — SHOW UPLOAD PAGE
    # =========================================================

    return render_template(
        "pyq.html",
        upload=True
    )
# ============================================================
# PREVIEW PYQ PDF
# ============================================================

@pyq.route(
    "/preview/<int:pyq_id>"
)
@login_required
def preview_pyq(pyq_id):

    pyq_item = PYQ.query.get_or_404(
        pyq_id
    )

    # Only approved PYQs can be previewed
    if pyq_item.verification_status != "approved":

        flash(
            "This PYQ is not available for preview.",
            "danger"
        )

        return redirect(
            url_for(
                "pyq.pyq_repository"
            )
        )

    # ---------------------------------------------------------
    # CHECK AWS S3 FIRST
    # ---------------------------------------------------------

    s3_key = get_pyq_s3_key(
        pyq_item
    )

    if object_exists(s3_key):

        file_url = generate_presigned_url(
            s3_key,
            download=False,
            download_name=pyq_item.file_name,
            expires=300
        )

        if file_url:

            # -----------------------------------------------------
            # RECORD STUDYHUB VIEW ACTIVITY
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
                        'pyq',
                        :resource_id,
                        'viewed'
                    )
                """),
                {
                    "user_id": current_user.id,
                    "resource_id": pyq_item.id
                }
            )

            db.session.commit()

            return redirect(file_url)

    # ---------------------------------------------------------
    # LEGACY LOCAL FILE FALLBACK
    # ---------------------------------------------------------

    if is_legacy_local_pyq(
        pyq_item
    ):

        file_path = get_file_path(
            pyq_item.file_name,
            category="pyq"
        )

        # -----------------------------------------------------
        # RECORD STUDYHUB VIEW ACTIVITY
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
                    'pyq',
                    :resource_id,
                    'viewed'
                )
            """),
            {
                "user_id": current_user.id,
                "resource_id": pyq_item.id
            }
        )

        db.session.commit()

        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=False
        )
    flash(
        "The requested PDF could not be found.",
        "danger"
    )

    return redirect(
        url_for(
            "pyq.pyq_repository"
        )
    )

# ============================================================
# DOWNLOAD PYQ
# ============================================================

@pyq.route(
    "/download/<int:pyq_id>"
)
@login_required
def download_pyq(pyq_id):

    pyq_item = PYQ.query.get_or_404(
        pyq_id
    )

    # Only approved PYQs can be downloaded
    if pyq_item.verification_status != "approved":

        flash(
            "This PYQ is not available for download.",
            "danger"
        )

        return redirect(
            url_for(
                "pyq.pyq_repository"
            )
        )

    # ---------------------------------------------------------
    # CHECK AWS S3 FIRST
    # ---------------------------------------------------------

    s3_key = get_pyq_s3_key(
        pyq_item
    )

    if object_exists(s3_key):

        file_url = generate_presigned_url(
            s3_key,
            download=True,
            download_name=pyq_item.file_name,
            expires=300
        )

        if file_url:

            pyq_item.downloads = (
                (pyq_item.downloads or 0)
                + 1
            )

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
                        'pyq',
                        :resource_id,
                        'downloaded'
                    )
                """),
                {
                    "user_id": current_user.id,
                    "resource_id": pyq_item.id
                }
            )

            db.session.commit()

            return redirect(file_url)

    # ---------------------------------------------------------
    # LEGACY LOCAL FILE FALLBACK
    # ---------------------------------------------------------

    if is_legacy_local_pyq(pyq_item):

        file_path = get_file_path(
            pyq_item.file_name,
            category="pyq"
        )

        pyq_item.downloads = (
            (pyq_item.downloads or 0)
            + 1
        )

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
                    'pyq',
                    :resource_id,
                    'downloaded'
                )
            """),
            {
                "user_id": current_user.id,
                "resource_id": pyq_item.id
            }
        )

        db.session.commit()

        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=True
        )

    flash(
        "The requested file could not be found.",
        "danger"
    )

    return redirect(
        url_for(
            "pyq.pyq_repository"
        )
    )

# ============================================================
# PYQ INTELLIGENCE + PREPARE SMART
# ============================================================

@pyq.route("/intelligence")
@login_required
def pyq_intelligence():

    selected_education_level = request.args.get(
        "education_level", ""
    ).strip()

    selected_course = request.args.get(
        "course", ""
    ).strip()

    selected_semester = request.args.get(
        "semester", ""
    ).strip()

    selected_subject = request.args.get(
        "subject", ""
    ).strip()

    selected_exam_session = request.args.get(
        "exam_session", ""
    ).strip()

    # ---------------------------------------------------------
    # FILTER OPTIONS
    # ---------------------------------------------------------

    available_education_levels = [
        value[0]
        for value in db.session.query(
            PYQ.education_level
        ).filter(
            PYQ.education_level.isnot(None)
        ).distinct().order_by(
            PYQ.education_level
        ).all()
        if value[0]
    ]

    available_courses = [
        value[0]
        for value in db.session.query(
            PYQ.course
        ).filter(
            PYQ.course.isnot(None)
        ).distinct().order_by(
            PYQ.course
        ).all()
        if value[0]
    ]

    available_semesters = [
        value[0]
        for value in db.session.query(
            PYQ.semester
        ).filter(
            PYQ.semester.isnot(None)
        ).distinct().order_by(
            PYQ.semester
        ).all()
        if value[0]
    ]

    available_subjects = [
        value[0]
        for value in db.session.query(
            PYQ.subject
        ).filter(
            PYQ.subject.isnot(None)
        ).distinct().order_by(
            PYQ.subject
        ).all()
        if value[0]
    ]

    available_exam_sessions = [
        value[0]
        for value in db.session.query(
            PYQ.exam_session
        ).filter(
            PYQ.exam_session.isnot(None)
        ).distinct().order_by(
            PYQ.exam_session
        ).all()
        if value[0]
    ]

    # ---------------------------------------------------------
    # APPLY FILTERS
    # ---------------------------------------------------------

    query = PYQ.query.filter(
        PYQ.verification_status == "approved"
    )

    if selected_education_level:
        query = query.filter(
            PYQ.education_level
            == selected_education_level
        )

    if selected_course:
        query = query.filter(
            PYQ.course
            == selected_course
        )

    if selected_semester:
        query = query.filter(
            PYQ.semester
            == selected_semester
        )

    if selected_subject:
        query = query.filter(
            PYQ.subject
            == selected_subject
        )

    if selected_exam_session:
        query = query.filter(
            PYQ.exam_session
            == selected_exam_session
        )

    papers = query.order_by(
        PYQ.exam_year.asc(),
        PYQ.id.asc()
    ).all()

    # ---------------------------------------------------------
    # EXTRACT QUESTIONS
    # ---------------------------------------------------------

    all_questions = []
    question_metadata = []

    # ---------------------------------------------------------
    # VISUAL DATA BY PAPER
    # ---------------------------------------------------------

    visual_by_paper = {}

    for paper in papers:

        visual_by_paper[paper.id] = []

        if not paper.visual_analysis:
            continue

        try:
            visual_data = json.loads(
                paper.visual_analysis
            )

            if isinstance(visual_data, list):

                visual_by_paper[paper.id] = (
                    visual_data
                )

        except Exception as exc:

            print(
                "[PYQ Visual Mapping Error]:",
                exc
            )

    total_questions = 0

    for paper in papers:

        parsed = []

        # Use cached parsed questions first
        if paper.parsed_questions:

            try:
                parsed = json.loads(
                    paper.parsed_questions
                )

            except Exception:
                parsed = []

        # Fallback: parse extracted text
        if not parsed and paper.extracted_text:

            try:
                parsed = parse_questions(
                    paper.extracted_text
                ) or []

            except Exception as e:

                print(
                    "Intelligence parsing error:",
                    e
                )

                parsed = []

            # Cache the result
            if parsed:

                paper.parsed_questions = json.dumps(
                    parsed,
                    ensure_ascii=False
                )

        for question in parsed:

            if not question:
                continue

            question = str(
                question
            ).strip()

            if len(question) < 10:
                continue

            all_questions.append(
                question
            )

            question_metadata.append(
                {
                    "question": question,
                    "paper_id": paper.id,
                    "title": paper.title,
                    "year": paper.exam_year,
                    "session": paper.exam_session,
                    "subject": paper.subject,
                    "course": paper.course,

                    # -------------------------------------------------
                    # RELATED VISUAL PAGES
                    # -------------------------------------------------

                    "visuals": visual_by_paper.get(
                        paper.id,
                        []
                    )
                }
            )

            total_questions += 1

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

    # ---------------------------------------------------------
    # FIND SIMILAR / REPEATED QUESTIONS
    # ---------------------------------------------------------

    repeated_groups = group_similar_questions(
        all_questions,
        threshold=0.45
    )

    metadata_by_question = {}

    for metadata in question_metadata:

        key = metadata["question"]

        metadata_by_question.setdefault(
            key,
            []
        ).append(
            metadata
        )

    repeated_questions = []
    topic_frequency = {}

    # ---------------------------------------------------------
    # BUILD REPEATED QUESTION DATA
    # ---------------------------------------------------------

    for group in repeated_groups:

        if not group:
            continue

        group_metadata = []
        occurrence_counter = {}

        for question in group:

            occurrence_index = (
                occurrence_counter.get(
                    question,
                    0
                )
            )

            metadata_list = (
                metadata_by_question.get(
                    question,
                    []
                )
            )

            if occurrence_index < len(
                metadata_list
            ):

                group_metadata.append(
                    metadata_list[
                        occurrence_index
                    ]
                )

            occurrence_counter[question] = (
                occurrence_index + 1
            )

        # A repeated question must occur
        # in at least two different papers.
        unique_paper_ids = {
            item["paper_id"]
            for item in group_metadata
        }

        if len(unique_paper_ids) < 2:
            continue

        years = sorted(
            {
                item["year"]
                for item in group_metadata
                if item.get("year")
            }
        )

        topic = get_group_topic(
            group
        )

        topic_name = topic.get(
            "name",
            "General"
        )

        topic_frequency[
            topic_name
        ] = (
            topic_frequency.get(
                topic_name,
                0
            ) + 1
        )

        # Use an actual question from the latest appearance
        # instead of arbitrarily selecting group[0].
        if group_metadata:
            latest_question_metadata = max(
                group_metadata,
                key=lambda item: (
                    item.get("year") or 0,
                    item.get("paper_id") or 0
                )
            )

            representative_question = (
                latest_question_metadata["question"]
            )
        else:
            representative_question = group[0]

        appearances = []
        seen_appearance_keys = set()

        for item in group_metadata:

            appearance_key = (
                item["paper_id"],
                item["question"]
            )

            if appearance_key in seen_appearance_keys:
                continue

            seen_appearance_keys.add(
                appearance_key
            )

            appearances.append(
                {
                    "paper_id": item["paper_id"],
                    "year": item["year"],
                    "session": item["session"],
                    "subject": item["subject"],
                    "title": item["title"],
                    "question": item["question"],

                    # -------------------------------------------------
                    # VISUAL CONTENT FROM THIS PAPER
                    # -------------------------------------------------

                    "visuals": item.get(
                        "visuals",
                        []
                    )
                }
            )

        appearances.sort(
            key=lambda x: (
                x["year"] or 0,
                x["paper_id"] or 0
            )
        )

        repeated_questions.append(
            {
                "question": representative_question,

                "topic": topic_name,

                # -------------------------------------------------
                # ALL VISUALS ASSOCIATED WITH THIS QUESTION GROUP
                # -------------------------------------------------

                "visuals": [
                    visual
                    for appearance in appearances
                    for visual in appearance.get(
                        "visuals",
                        []
                    )
                ],

                "matched_keywords": topic.get(
                    "matched_keywords",
                    []
                ),

                "count": len(
                    unique_paper_ids
                ),

                "years": years,

                "appearances": appearances,

                "variants": group
            }
        )

    # ---------------------------------------------------------
    # BASIC SORTING
    # ---------------------------------------------------------

    repeated_questions.sort(
        key=lambda item: (
            item["count"],
            len(item["years"])
        ),
        reverse=True
    )

    sorted_topic_frequency = sorted(
        topic_frequency.items(),
        key=lambda item: item[1],
        reverse=True
    )

    # ---------------------------------------------------------
    # PHASE 3 - PREPARE SMART
    # ---------------------------------------------------------

    analyzed_years = sorted(
        {
            paper.exam_year
            for paper in papers
            if paper.exam_year
        }
    )

    latest_analyzed_year = (
        analyzed_years[-1]
        if analyzed_years
        else None
    )

    prepare_smart = []

    for item in repeated_questions:

        appearances = item.get(
            "appearances",
            []
        )

        latest_year = None
        latest_session = None

        if appearances:

            latest_appearance = max(
                appearances,
                key=lambda appearance: (
                    appearance.get("year") or 0,
                    appearance.get("paper_id") or 0
                )
            )

            latest_year = latest_appearance.get(
                "year"
            )

            latest_session = latest_appearance.get(
                "session"
            )

        # Percentage of analyzed papers
        frequency_percent = 0

        if papers:

            frequency_percent = round(
                (
                    item["count"]
                    / len(papers)
                ) * 100
            )

        # Appeared in the latest analyzed year?
        recently_seen = (
            latest_analyzed_year is not None
            and latest_year == latest_analyzed_year
        )

        not_recently_seen = (
            latest_analyzed_year is not None
            and latest_year is not None
            and latest_year < latest_analyzed_year
        )

        # Historical study classification.
        # This is NOT an exam prediction.
        if (
            item["count"] >= 3
            and not_recently_seen
        ):

            study_status = "High Priority"

        elif (
            item["count"] >= 2
            and not_recently_seen
        ):

            study_status = "Review Soon"

        elif recently_seen:

            study_status = "Recently Appeared"

        else:

            study_status = "Repeated"

        prepare_smart.append(
            {
                "question": item["question"],

                "topic": item["topic"],

                "visuals": item.get(
                    "visuals",
                    []
                ),

                "count": item["count"],

                "frequency_percent": frequency_percent,

                "years": item["years"],

                "latest_year": latest_year,

                "latest_session": latest_session,

                "recently_seen": recently_seen,

                "not_recently_seen": not_recently_seen,

                "study_status": study_status
            }
        )

    # ---------------------------------------------------------
    # SORT PREPARE SMART
    # ---------------------------------------------------------

    prepare_smart.sort(
        key=lambda item: (
            item["not_recently_seen"],
            item["count"],
            item["frequency_percent"]
        ),
        reverse=True
    )

    # ---------------------------------------------------------
    # TOPIC-WISE PREPARATION
    # ---------------------------------------------------------

    topic_details = {}

    for item in repeated_questions:

        topic = item["topic"]

        if topic not in topic_details:

            topic_details[topic] = {
                "topic": topic,
                "group_count": 0,
                "paper_appearances": 0,
                "latest_year": None,
                "questions": []
            }

        topic_details[topic]["group_count"] += 1

        topic_details[topic]["paper_appearances"] += (
            item["count"]
        )

        if item["years"]:

            topic_latest_year = max(
                item["years"]
            )

            current_latest = (
                topic_details[topic]["latest_year"]
            )

            if (
                current_latest is None
                or topic_latest_year > current_latest
            ):

                topic_details[topic]["latest_year"] = (
                    topic_latest_year
                )

        topic_details[topic]["questions"].append(
            item["question"]
        )

    prepare_topics = list(
        topic_details.values()
    )

    prepare_topics.sort(
        key=lambda item: (
            item["group_count"],
            item["paper_appearances"]
        ),
        reverse=True
    )

    # ---------------------------------------------------------
    # PREPARE SMART SUMMARY
    # ---------------------------------------------------------

    frequently_repeated_count = sum(
        1
        for item in prepare_smart
        if item["count"] >= 3
    )

    not_recently_seen_count = sum(
        1
        for item in prepare_smart
        if item["not_recently_seen"]
    )

    recently_seen_count = sum(
        1
        for item in prepare_smart
        if item["recently_seen"]
    )

    coverage = {
        "papers": len(papers),

        "questions": total_questions,

        "repeated_groups": len(
            repeated_questions
        ),

        "topics": len(
            topic_frequency
        )
    }

    prepare_summary = {
        "frequently_repeated": (
            frequently_repeated_count
        ),

        "not_recently_seen": (
            not_recently_seen_count
        ),

        "recently_seen": (
            recently_seen_count
        ),

        "topics": len(
            prepare_topics
        ),

        "latest_year": latest_analyzed_year
    }

    # =========================================================
    # ANALYTICS DASHBOARD
    # =========================================================

    # ---------------------------------------------------------
    # 1. YEAR-WISE PAPER FREQUENCY
    # ---------------------------------------------------------

    year_frequency_map = {}

    for paper in papers:

        if not paper.exam_year:
            continue

        year = int(paper.exam_year)

        year_frequency_map[year] = (
            year_frequency_map.get(year, 0) + 1
        )

    year_frequency = [
        {
            "year": year,
            "count": count
        }
        for year, count in sorted(
            year_frequency_map.items()
        )
    ]

    # ---------------------------------------------------------
    # 2. YEAR-WISE QUESTION FREQUENCY
    # ---------------------------------------------------------

    year_question_map = {}

    for metadata in question_metadata:

        year = metadata.get("year")

        if not year:
            continue

        year = int(year)

        year_question_map[year] = (
            year_question_map.get(year, 0) + 1
        )

    year_question_frequency = [
        {
            "year": year,
            "count": count
        }
        for year, count in sorted(
            year_question_map.items()
        )
    ]

    # ---------------------------------------------------------
    # 3. SUBJECT FREQUENCY
    # ---------------------------------------------------------

    subject_frequency_map = {}

    for paper in papers:

        subject_name = (
            paper.subject
            or "Unknown"
        )

        subject_frequency_map[subject_name] = (
            subject_frequency_map.get(
                subject_name,
                0
            ) + 1
        )

    subject_frequency = sorted(
        [
            {
                "subject": subject,
                "count": count
            }
            for subject, count
            in subject_frequency_map.items()
        ],
        key=lambda item: item["count"],
        reverse=True
    )[:10]

    # ---------------------------------------------------------
    # 4. REPETITION DISTRIBUTION
    # ---------------------------------------------------------

    repetition_distribution = {
        "once": 0,
        "twice": 0,
        "three_plus": 0
    }

    for item in repeated_questions:

        count = item.get(
            "count",
            0
        )

        if count == 2:

            repetition_distribution["twice"] += 1

        elif count >= 3:

            repetition_distribution["three_plus"] += 1

    repeated_question_count = sum(
        item.get("count", 0)
        for item in repeated_questions
    )

    single_occurrence_count = max(
        total_questions - repeated_question_count,
        0
    )

    repetition_distribution["once"] = (
        single_occurrence_count
    )

    # ---------------------------------------------------------
    # 5. TOP TOPICS
    # ---------------------------------------------------------

    top_topics = [
        {
            "topic": topic,
            "count": count
        }
        for topic, count
        in sorted_topic_frequency[:10]
    ]

    # ---------------------------------------------------------
    # 6. RECENT VS HISTORICAL
    # ---------------------------------------------------------

    recent_question_count = 0
    historical_question_count = 0

    if latest_analyzed_year is not None:

        for metadata in question_metadata:

            year = metadata.get("year")

            if not year:
                continue

            if int(year) == int(
                latest_analyzed_year
            ):

                recent_question_count += 1

            else:

                historical_question_count += 1

    # ---------------------------------------------------------
    # 7. LATEST YEAR SUMMARY
    # ---------------------------------------------------------

    previous_year = None

    if len(analyzed_years) >= 2:

        previous_year = analyzed_years[-2]

    latest_year_papers = 0
    previous_year_papers = 0

    if latest_analyzed_year:

        latest_year_papers = (
            year_frequency_map.get(
                latest_analyzed_year,
                0
            )
        )

    if previous_year:

        previous_year_papers = (
            year_frequency_map.get(
                previous_year,
                0
            )
        )

    # ---------------------------------------------------------
    # 8. ANALYTICS SUMMARY
    # ---------------------------------------------------------

    analytics_summary = {

        "latest_year": latest_analyzed_year,

        "previous_year": previous_year,

        "latest_year_papers": (
            latest_year_papers
        ),

        "previous_year_papers": (
            previous_year_papers
        ),

        "recent_questions": (
            recent_question_count
        ),

        "historical_questions": (
            historical_question_count
        ),

        "repeated_groups": len(
            repeated_questions
        ),

        "top_topic": (
            top_topics[0]["topic"]
            if top_topics
            else None
        )
    }

    # =========================================================
    # VISUAL INTELLIGENCE
    # =========================================================
    #
    # IMPORTANT:
    # Visual analysis is already performed during PYQ upload and
    # stored in PYQ.visual_analysis as JSON.
    #
    # Do NOT run PyMuPDF + Tesseract for every page request.
    # That made /pyq/intelligence extremely slow.
    #
    # We read the stored results here instead. New uploads will
    # automatically contain fresh visual analysis.
    # =========================================================

    visual_analysis = []

    visual_figures_count = 0
    visual_tables_count = 0
    visual_graphs_count = 0
    visual_pages_count = 0

    seen_visual_pages = set()

    for paper in papers:

        if not paper.visual_analysis:
            continue

        try:

            stored_visuals = json.loads(
                paper.visual_analysis
            )

        except Exception as visual_error:

            print(
                "[StudyHub Visual Intelligence] "
                f"Invalid stored visual data for "
                f"{paper.file_name}: {visual_error}"
            )

            continue

        if not isinstance(
            stored_visuals,
            list
        ):
            continue

        for stored_visual in stored_visuals:

            if not isinstance(
                stored_visual,
                dict
            ):
                continue

            page_key = (
                paper.id,
                stored_visual.get("page")
            )

            if page_key in seen_visual_pages:
                continue

            seen_visual_pages.add(
                page_key
            )

            visual = dict(
                stored_visual
            )

            visual["paper_id"] = (
                paper.id
            )

            visual["paper_title"] = (
                paper.title
            )

            visual["paper_year"] = (
                paper.exam_year
            )

            visual["paper_subject"] = (
                paper.subject
            )

            visual["paper_session"] = (
                paper.exam_session
            )

            # Older stored visual-analysis records may contain
            # image_path but not image_filename. Recover the
            # filename without rerunning PDF analysis/OCR.
            if not visual.get("image_filename"):
                image_path = (
                    visual.get("image_path")
                    or ""
                )

                if image_path:
                    visual["image_filename"] = (
                        os.path.basename(
                            image_path
                        )
                    )

            visual_analysis.append(
                visual
            )

            visual_type = (
                visual.get("visual_type")
                or ""
            ).lower()

            if "table" in visual_type:

                visual_tables_count += 1

            elif (
                "graph" in visual_type
                or "chart" in visual_type
            ):

                visual_graphs_count += 1

            else:

                visual_figures_count += 1


    # Total unique visual pages
    visual_pages_count = len(
        visual_analysis
    )

    # The UI displays only the first 8.
    # Keep a larger limit for future sections.
    visual_analysis = visual_analysis[:100]

    # =========================================================
    # RENDER PYQ INTELLIGENCE PAGE
    # =========================================================

    return render_template(
        "pyq_intelligence.html",

        # -----------------------------------------------------
        # MAIN PYQ DATA
        # -----------------------------------------------------

        papers=papers,

        repeated_questions=(
            repeated_questions
        ),

        topic_frequency=(
            sorted_topic_frequency
        ),

        prepare_smart=(
            prepare_smart
        ),

        prepare_topics=(
            prepare_topics
        ),

        prepare_summary=(
            prepare_summary
        ),

        coverage=coverage,

        # -----------------------------------------------------
        # FILTER VALUES
        # -----------------------------------------------------

        selected_education_level=(
            selected_education_level
        ),

        selected_course=(
            selected_course
        ),

        selected_semester=(
            selected_semester
        ),

        selected_subject=(
            selected_subject
        ),

        selected_exam_session=(
            selected_exam_session
        ),

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

        available_exam_sessions=(
            available_exam_sessions
        ),

        # =====================================================
        # ANALYTICS DASHBOARD DATA
        # =====================================================

        analytics_summary=(
            analytics_summary
        ),

        year_frequency=(
            year_frequency
        ),

        year_question_frequency=(
            year_question_frequency
        ),

        subject_frequency=(
            subject_frequency
        ),

        repetition_distribution=(
            repetition_distribution
        ),

        top_topics=(
            top_topics
        ),

        # =====================================================
        # VISUAL INTELLIGENCE DATA
        # =====================================================

        visual_analysis=(
            visual_analysis
        ),

        visual_figures_count=(
            visual_figures_count
        ),

        visual_tables_count=(
            visual_tables_count
        ),

        visual_graphs_count=(
            visual_graphs_count
        ),

        visual_pages_count=(
            visual_pages_count
        )
    )

# ============================================================
# REPORT PYQ
# ============================================================

@pyq.route(
    "/<int:pyq_id>/report",
    methods=["POST"]
)
@login_required
def report_pyq(pyq_id):

    pyq_item = PYQ.query.get_or_404(pyq_id)

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
            "Please select a reason for reporting this PYQ.",
            "warning"
        )

        return redirect(
            url_for(
                "pyq.preview_pyq",
                pyq_id=pyq_item.id
            )
        )

    report = ResourceReport(

        user_id=current_user.id,

        resource_type="pyq",

        resource_id=pyq_item.id,

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
            "pyq.preview_pyq",
            pyq_id=pyq_item.id
        )
    )