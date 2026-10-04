import re

from flask import url_for

from app.models import Note, PYQ


# =========================================================
# BASIC HELPERS
# =========================================================

def normalize_text(text):

    if not text:
        return ""

    return " ".join(
        text.lower().strip().split()
    )


def contains_any(text, words):

    text = normalize_text(text)

    return any(
        word in text
        for word in words
    )


def detect_subject(text):

    text = normalize_text(text)

    subjects = {

        "DBMS": [
            "dbms",
            "database",
            "database management"
        ],

        "Computer Networks": [
            "computer network",
            "computer networks",
            "networking",
            "cn"
        ],

        "Data Structures": [
            "data structure",
            "data structures",
            "ds"
        ],

        "Operating Systems": [
            "operating system",
            "operating systems",
            "os"
        ],

        "Artificial Intelligence": [
            "artificial intelligence",
            "ai"
        ],

        "Discrete Mathematics": [
            "discrete mathematics",
            "discrete mathematical",
            "dms"
        ]
    }

    for subject, aliases in subjects.items():

        for alias in aliases:

            if alias in text:
                return subject

    return None


def detect_year(text):

    match = re.search(
        r"\b(20\d{2})\b",
        text
    )

    if match:
        return int(
            match.group(1)
        )

    return None


def detect_course(text):

    text = normalize_text(text)

    if "computer science" in text:
        return "Computer Science and Engineering"

    if "cse" in text:
        return "Computer Science and Engineering"

    if "information science" in text:
        return "Information Science and Engineering"

    if "ise" in text:
        return "Information Science and Engineering"

    if "electronics" in text:
        return "Electronics and Communication Engineering"

    return None


# =========================================================
# PYQ SEARCH
# =========================================================

def search_pyqs(
    subject=None,
    year=None,
    course=None
):

    query = PYQ.query.filter_by(
        verification_status="approved"
    )

    if subject:

        query = query.filter(
            PYQ.subject.ilike(
                f"%{subject}%"
            )
        )

    if year:

        query = query.filter(
            PYQ.exam_year == year
        )

    if course:

        query = query.filter(
            PYQ.course.ilike(
                f"%{course}%"
            )
        )

    return query.order_by(
        PYQ.exam_year.desc(),
        PYQ.views.desc()
    ).limit(10).all()


# =========================================================
# RECENT PYQs
# =========================================================

def get_recent_pyqs(subject=None):

    query = PYQ.query.filter_by(
        verification_status="approved"
    )

    if subject:

        query = query.filter(
            PYQ.subject.ilike(
                f"%{subject}%"
            )
        )

    return query.order_by(
        PYQ.exam_year.desc()
    ).limit(10).all()


# =========================================================
# NOTE SEARCH
# =========================================================

def search_notes(
    subject=None,
    course=None
):

    query = Note.query.filter_by(
        verification_status="approved"
    )

    if subject:

        query = query.filter(
            Note.subject.ilike(
                f"%{subject}%"
            )
        )

    if course:

        query = query.filter(
            Note.course.ilike(
                f"%{course}%"
            )
        )

    return query.order_by(
        Note.downloads.desc(),
        Note.views.desc()
    ).limit(10).all()


# =========================================================
# RECENT NOTES
# =========================================================

def get_recent_notes(subject=None):

    query = Note.query.filter_by(
        verification_status="approved"
    )

    if subject:

        query = query.filter(
            Note.subject.ilike(
                f"%{subject}%"
            )
        )

    return query.order_by(
        Note.uploaded_at.desc()
    ).limit(10).all()


# =========================================================
# AI PROCESSOR
# =========================================================

def process_question(message):

    text = normalize_text(
        message
    )

    if not text:

        return {
            "type": "general",
            "message": "Please enter a question."
        }


    subject = detect_subject(
        text
    )

    year = detect_year(
        text
    )

    course = detect_course(
        text
    )


    # =====================================================
    # NOTES
    # =====================================================

    if contains_any(
        text,
        [
            "notes",
            "note",
            "study material",
            "study materials"
        ]
    ):

        notes = search_notes(
            subject=subject,
            course=course
        )

        result = []

        for note in notes:

            result.append({

                "title": note.title,

                "subject": note.subject,

                "url": url_for(
                    "notes.view_note",
                    note_id=note.id
                )
            })

        return {

            "type": "notes",

            "message": (
                f"Here are the available "
                f"{subject or 'study'} notes."
            ),

            "results": result
        }


    # =====================================================
    # PYQs
    # =====================================================

    if contains_any(
        text,
        [
            "pyq",
            "pyqs",
            "previous year",
            "previous question",
            "question paper",
            "question papers"
        ]
    ):

        pyqs = search_pyqs(
            subject=subject,
            year=year,
            course=course
        )

        result = []

        for pyq in pyqs:

            result.append({

                "title": pyq.title,

                "subject": pyq.subject,

                "year": pyq.exam_year,

                "url": url_for(
                    "pyq.view_pyq",
                    pyq_id=pyq.id
                )
            })

        return {

            "type": "pyqs",

            "message": (
                f"Here are the available "
                f"{subject or 'previous-year'} papers."
            ),

            "results": result
        }


    # =====================================================
    # REPEATED QUESTIONS
    # =====================================================

    if contains_any(
        text,
        [
            "repeated",
            "repeat",
            "frequently asked",
            "frequent questions",
            "important questions"
        ]
    ):

        return {

            "type": "repeated",

            "message": (
                "Use PYQ Intelligence to analyze "
                "repeated questions, question frequency "
                "and historical appearances."
            ),

            "url": url_for(
                "pyq.pyq_intelligence"
            )
        }


    # =====================================================
    # PREPARE SMART
    # =====================================================

    if contains_any(
        text,
        [
            "prepare smart",
            "prepare",
            "what should i study",
            "what should i learn",
            "study plan"
        ]
    ):

        return {

            "type": "prepare",

            "message": (
                "StudyHub can help you prioritize "
                "historically frequent topics and "
                "repeated questions using PYQ Intelligence."
            ),

            "url": url_for(
                "pyq.pyq_intelligence"
            )
        }


    # =====================================================
    # TRENDING
    # =====================================================

    if contains_any(
        text,
        [
            "trending",
            "popular",
            "most downloaded",
            "most viewed"
        ]
    ):

        return {

            "type": "recommendations",

            "message": (
                "You can explore popular and "
                "personalized StudyHub resources."
            ),

            "url": url_for(
                "recommendations.home"
            )
        }


    # =====================================================
    # GENERAL
    # =====================================================

    return {

        "type": "general",

        "message": (
            "I can help you find notes, PYQs, "
            "repeated questions, frequently studied "
            "topics and academic resources."
        )
    }