from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required

from app import db, limiter
from app.models import Note, PYQ


search = Blueprint(
    "search",
    __name__,
    url_prefix="/search"
)


# =========================================================
# HELPER — SEARCH SCORE
# =========================================================

def calculate_score(
    query,
    title="",
    subject="",
    course="",
    education_level="",
    semester="",
    description="",
    exam_session=""
):

    query = (query or "").strip().lower()

    title = (title or "").lower()
    subject = (subject or "").lower()
    course = (course or "").lower()
    education_level = (education_level or "").lower()
    semester = (semester or "").lower()
    description = (description or "").lower()
    exam_session = (exam_session or "").lower()

    score = 0


    # Exact title
    if title == query:
        score += 100


    # Title starts with query
    elif title.startswith(query):
        score += 80


    # Query appears in title
    elif query in title:
        score += 60


    # Subject
    if subject == query:
        score += 70

    elif query in subject:
        score += 45


    # Course
    if course == query:
        score += 50

    elif query in course:
        score += 30


    # Education level
    if query in education_level:
        score += 20


    # Semester
    if query in semester:
        score += 15


    # Description
    if query in description:
        score += 10


    # Exam session
    if query in exam_session:
        score += 10


    return score


# =========================================================
# GLOBAL SEARCH PAGE
# =========================================================

@search.route("/")
@login_required
@limiter.limit("60 per minute")
def global_search():

    query_text = request.args.get(
        "q",
        ""
    ).strip()

    resource_type = request.args.get(
        "type",
        "all"
    ).strip().lower()


    if resource_type not in {
        "all",
        "notes",
        "pyqs"
    }:

        resource_type = "all"


    notes_results = []
    pyq_results = []


    if query_text:

        search_value = f"%{query_text}%"


        # =================================================
        # NOTES
        # =================================================

        if resource_type in {
            "all",
            "notes"
        }:

            notes = (
                Note.query
                .filter(
                    Note.verification_status
                    == "approved"
                )
                .filter(
                    db.or_(
                        Note.title.ilike(
                            search_value
                        ),

                        Note.description.ilike(
                            search_value
                        ),

                        Note.subject.ilike(
                            search_value
                        ),

                        Note.course.ilike(
                            search_value
                        ),

                        Note.education_level.ilike(
                            search_value
                        ),

                        Note.semester.ilike(
                            search_value
                        )
                    )
                )
                .limit(50)
                .all()
            )


            for note in notes:

                score = calculate_score(

                    query_text,

                    title=note.title,

                    subject=note.subject,

                    course=note.course,

                    education_level=
                        note.education_level,

                    semester=note.semester,

                    description=note.description

                )

                notes_results.append(
                    (score, note)
                )


            notes_results.sort(
                key=lambda item: item[0],
                reverse=True
            )


            notes_results = [
                note
                for score, note
                in notes_results[:30]
            ]


        # =================================================
        # PYQs
        # =================================================

        if resource_type in {
            "all",
            "pyqs"
        }:

            pyqs = (
                PYQ.query
                .filter(
                    PYQ.verification_status
                    == "approved"
                )
                .filter(
                    db.or_(
                        PYQ.title.ilike(
                            search_value
                        ),

                        PYQ.subject.ilike(
                            search_value
                        ),

                        PYQ.course.ilike(
                            search_value
                        ),

                        PYQ.education_level.ilike(
                            search_value
                        ),

                        PYQ.semester.ilike(
                            search_value
                        ),

                        PYQ.exam_session.ilike(
                            search_value
                        )
                    )
                )
                .limit(50)
                .all()
            )


            for paper in pyqs:

                score = calculate_score(

                    query_text,

                    title=paper.title,

                    subject=paper.subject,

                    course=paper.course,

                    education_level=
                        paper.education_level,

                    semester=paper.semester,

                    exam_session=
                        paper.exam_session

                )

                pyq_results.append(
                    (score, paper)
                )


            pyq_results.sort(
                key=lambda item: (
                    item[0],
                    item[1].exam_year or 0
                ),
                reverse=True
            )


            pyq_results = [
                paper
                for score, paper
                in pyq_results[:30]
            ]


    total_results = (
        len(notes_results)
        +
        len(pyq_results)
    )


    return render_template(

        "search.html",

        query_text=query_text,

        resource_type=resource_type,

        notes_results=notes_results,

        pyq_results=pyq_results,

        total_results=total_results

    )


# =========================================================
# AJAX SEARCH API
# =========================================================

@search.route("/api")
@login_required
@limiter.limit("60 per minute")
def search_api():

    query_text = request.args.get(
        "q",
        ""
    ).strip()

    resource_type = request.args.get(
        "type",
        "all"
    ).strip().lower()


    if resource_type not in {
        "all",
        "notes",
        "pyqs"
    }:

        resource_type = "all"


    # -----------------------------------------------------
    # EMPTY SEARCH
    # -----------------------------------------------------

    if not query_text:

        return jsonify({

            "query": "",

            "total": 0,

            "notes": [],

            "pyqs": []

        })


    search_value = (
        f"%{query_text}%"
    )


    notes_output = []
    pyqs_output = []


    # =====================================================
    # NOTES
    # =====================================================

    if resource_type in {
        "all",
        "notes"
    }:

        notes = (
            Note.query
            .filter(
                Note.verification_status
                == "approved"
            )
            .filter(
                db.or_(
                    Note.title.ilike(
                        search_value
                    ),

                    Note.description.ilike(
                        search_value
                    ),

                    Note.subject.ilike(
                        search_value
                    ),

                    Note.course.ilike(
                        search_value
                    ),

                    Note.education_level.ilike(
                        search_value
                    ),

                    Note.semester.ilike(
                        search_value
                    )
                )
            )
            .limit(50)
            .all()
        )


        scored_notes = []


        for note in notes:

            score = calculate_score(

                query_text,

                title=note.title,

                subject=note.subject,

                course=note.course,

                education_level=
                    note.education_level,

                semester=note.semester,

                description=note.description

            )


            scored_notes.append(
                (score, note)
            )


        scored_notes.sort(
            key=lambda item: item[0],
            reverse=True
        )


        for score, note in scored_notes[:8]:

            notes_output.append({

                "id": note.id,

                "title":
                    note.title or "Untitled Note",

                "description":
                    (
                        note.description
                        or ""
                    )[:180],

                "subject":
                    note.subject or "",

                "course":
                    note.course or "",

                "semester":
                    note.semester or "",

                "icon":
                    "📚",

                "type":
                    "Note",

                "score":
                    score,

                "url":
                    f"/notes?search="
                    f"{str(note.title or '')}"

            })


    # =====================================================
    # PYQs
    # =====================================================

    if resource_type in {
        "all",
        "pyqs"
    }:

        pyqs = (
            PYQ.query
            .filter(
                PYQ.verification_status
                == "approved"
            )
            .filter(
                db.or_(
                    PYQ.title.ilike(
                        search_value
                    ),

                    PYQ.subject.ilike(
                        search_value
                    ),

                    PYQ.course.ilike(
                        search_value
                    ),

                    PYQ.education_level.ilike(
                        search_value
                    ),

                    PYQ.semester.ilike(
                        search_value
                    ),

                    PYQ.exam_session.ilike(
                        search_value
                    )
                )
            )
            .limit(50)
            .all()
        )


        scored_pyqs = []


        for paper in pyqs:

            score = calculate_score(

                query_text,

                title=paper.title,

                subject=paper.subject,

                course=paper.course,

                education_level=
                    paper.education_level,

                semester=paper.semester,

                exam_session=
                    paper.exam_session

            )


            scored_pyqs.append(
                (score, paper)
            )


        scored_pyqs.sort(

            key=lambda item: (
                item[0],
                item[1].exam_year or 0
            ),

            reverse=True

        )


        for score, paper in scored_pyqs[:8]:

            pyqs_output.append({

                "id":
                    paper.id,

                "title":
                    paper.title
                    or "Untitled PYQ",

                "description":
                    (
                        paper.subject
                        or paper.course
                        or ""
                    ),

                "subject":
                    paper.subject or "",

                "course":
                    paper.course or "",

                "semester":
                    paper.semester or "",

                "year":
                    paper.exam_year,

                "session":
                    paper.exam_session or "",

                "icon":
                    "📝",

                "type":
                    "PYQ",

                "score":
                    score,

                "url":
                    f"/pyq/?search="
                    f"{str(paper.title or '')}"

            })


    return jsonify({

        "query":
            query_text,

        "total":
            len(notes_output)
            +
            len(pyqs_output),

        "notes":
            notes_output,

        "pyqs":
            pyqs_output

    })