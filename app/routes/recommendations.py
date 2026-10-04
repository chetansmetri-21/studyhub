from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models import Note, PYQ


recommendations = Blueprint(
    "recommendations",
    __name__,
    url_prefix="/recommendations"
)


@recommendations.route("/")
@login_required
def home():

    # -------------------------------------------------
    # Recommended Notes
    # -------------------------------------------------

    notes_query = Note.query.filter_by(
        verification_status="approved"
    )

    if current_user.course:
        notes_query = notes_query.filter(
            Note.course == current_user.course
        )

    if current_user.semester:
        notes_query = notes_query.filter(
            Note.semester == current_user.semester
        )

    recommended_notes = notes_query.order_by(
        Note.downloads.desc(),
        Note.views.desc()
    ).limit(10).all()

    # -------------------------------------------------
    # Recommended PYQs
    # -------------------------------------------------

    pyq_query = PYQ.query.filter_by(
        verification_status="approved"
    )

    if current_user.course:
        pyq_query = pyq_query.filter(
            PYQ.course == current_user.course
        )

    if current_user.semester:
        pyq_query = pyq_query.filter(
            PYQ.semester == current_user.semester
        )

    recommended_pyqs = pyq_query.order_by(
        PYQ.downloads.desc(),
        PYQ.views.desc(),
        PYQ.exam_year.desc()
    ).limit(10).all()

    # -------------------------------------------------
    # Trending Notes
    # -------------------------------------------------

    trending_notes = Note.query.filter_by(
        verification_status="approved"
    ).order_by(
        Note.views.desc(),
        Note.downloads.desc()
    ).limit(6).all()

    # -------------------------------------------------
    # Trending PYQs
    # -------------------------------------------------

    trending_pyqs = PYQ.query.filter_by(
        verification_status="approved"
    ).order_by(
        PYQ.views.desc(),
        PYQ.downloads.desc(),
        PYQ.exam_year.desc()
    ).limit(6).all()

    return render_template(
        "recommendations.html",
        recommended_notes=recommended_notes,
        recommended_pyqs=recommended_pyqs,
        trending_notes=trending_notes,
        trending_pyqs=trending_pyqs
    )