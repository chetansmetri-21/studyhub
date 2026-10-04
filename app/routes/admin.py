from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from app import db

from app.models import (
    User,
    Note,
    PYQ
)


admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


# =========================================================
# ADMIN ACCESS CHECK
# =========================================================

def admin_required():

    if not current_user.is_authenticated:
        return False

    return bool(
        current_user.is_admin
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@admin.route("/")
@login_required
def dashboard():

    if not admin_required():

        flash(
            "Admin access required.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )


    total_users = User.query.count()

    total_notes = Note.query.count()

    total_pyqs = PYQ.query.count()


    pending_notes = Note.query.filter_by(
        verification_status="pending"
    ).count()

    pending_pyqs = PYQ.query.filter_by(
        verification_status="pending"
    ).count()


    approved_notes = Note.query.filter_by(
        verification_status="approved"
    ).count()

    approved_pyqs = PYQ.query.filter_by(
        verification_status="approved"
    ).count()


    rejected_notes = Note.query.filter_by(
        verification_status="rejected"
    ).count()

    rejected_pyqs = PYQ.query.filter_by(
        verification_status="rejected"
    ).count()


    recent_notes = Note.query.order_by(
        Note.uploaded_at.desc()
    ).limit(10).all()


    recent_pyqs = PYQ.query.order_by(
        PYQ.uploaded_at.desc()
    ).limit(10).all()


    pending_notes_list = Note.query.filter_by(
        verification_status="pending"
    ).order_by(
        Note.uploaded_at.desc()
    ).all()


    pending_pyqs_list = PYQ.query.filter_by(
        verification_status="pending"
    ).order_by(
        PYQ.uploaded_at.desc()
    ).all()


    users = User.query.order_by(
        User.id.desc()
    ).all()


    return render_template(
        "admin_dashboard.html",

        total_users=total_users,

        total_notes=total_notes,

        total_pyqs=total_pyqs,

        pending_notes=pending_notes,

        pending_pyqs=pending_pyqs,

        approved_notes=approved_notes,

        approved_pyqs=approved_pyqs,

        rejected_notes=rejected_notes,

        rejected_pyqs=rejected_pyqs,

        recent_notes=recent_notes,

        recent_pyqs=recent_pyqs,

        pending_notes_list=pending_notes_list,

        pending_pyqs_list=pending_pyqs_list,

        users=users
    )


# =========================================================
# APPROVE NOTE
# =========================================================

@admin.route(
    "/note/<int:note_id>/approve",
    methods=["POST"]
)
@login_required
def approve_note(note_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )


    note = Note.query.get_or_404(
        note_id
    )

    note.verification_status = "approved"

    db.session.commit()


    flash(
        "Note approved successfully.",
        "success"
    )


    return redirect(
        url_for("admin.dashboard")
    )


# =========================================================
# REJECT NOTE
# =========================================================

@admin.route(
    "/note/<int:note_id>/reject",
    methods=["POST"]
)
@login_required
def reject_note(note_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )


    note = Note.query.get_or_404(
        note_id
    )

    note.verification_status = "rejected"

    db.session.commit()


    flash(
        "Note rejected.",
        "warning"
    )


    return redirect(
        url_for("admin.dashboard")
    )


# =========================================================
# APPROVE PYQ
# =========================================================

@admin.route(
    "/pyq/<int:pyq_id>/approve",
    methods=["POST"]
)
@login_required
def approve_pyq(pyq_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )


    pyq = PYQ.query.get_or_404(
        pyq_id
    )

    pyq.verification_status = "approved"

    db.session.commit()


    flash(
        "PYQ approved successfully.",
        "success"
    )


    return redirect(
        url_for("admin.dashboard")
    )


# =========================================================
# REJECT PYQ
# =========================================================

@admin.route(
    "/pyq/<int:pyq_id>/reject",
    methods=["POST"]
)
@login_required
def reject_pyq(pyq_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )


    pyq = PYQ.query.get_or_404(
        pyq_id
    )

    pyq.verification_status = "rejected"

    db.session.commit()


    flash(
        "PYQ rejected.",
        "warning"
    )


    return redirect(
        url_for("admin.dashboard")
    )