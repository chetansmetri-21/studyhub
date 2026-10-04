from flask import (
    Blueprint,
    render_template,
    request,
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
    PYQ,
    ResourceRequest,
    Notification,
    CollaborativeNote,
    CollaborativeContribution
)


community = Blueprint(
    "community",
    __name__,
    url_prefix="/community"
)


# =========================================================
# COMMUNITY HOME
# =========================================================

@community.route("/")
@login_required
def home():

    # -----------------------------------------------------
    # TRENDING NOTES
    # -----------------------------------------------------

    trending_notes = (
        Note.query
        .filter_by(
            verification_status="approved"
        )
        .order_by(
            Note.views.desc(),
            Note.downloads.desc()
        )
        .limit(8)
        .all()
    )


    # -----------------------------------------------------
    # TRENDING PYQs
    # -----------------------------------------------------

    trending_pyqs = (
        PYQ.query
        .filter_by(
            verification_status="approved"
        )
        .order_by(
            PYQ.views.desc(),
            PYQ.downloads.desc()
        )
        .limit(8)
        .all()
    )


    # -----------------------------------------------------
    # OPEN RESOURCE REQUESTS
    # -----------------------------------------------------

    resource_requests = (
        ResourceRequest.query
        .filter_by(
            status="open"
        )
        .order_by(
            ResourceRequest.created_at.desc()
        )
        .limit(12)
        .all()
    )


    # -----------------------------------------------------
    # MY COLLABORATIVE NOTES
    # -----------------------------------------------------

    collaborative_notes = (
        CollaborativeNote.query
        .filter_by(
            owner_id=current_user.id
        )
        .order_by(
            CollaborativeNote.updated_at.desc()
        )
        .limit(10)
        .all()
    )


    # -----------------------------------------------------
    # UNREAD NOTIFICATIONS
    # -----------------------------------------------------

    unread_count = (
        Notification.query
        .filter_by(
            user_id=current_user.id,
            is_read=False
        )
        .count()
    )


    return render_template(
        "community.html",

        trending_notes=trending_notes,

        trending_pyqs=trending_pyqs,

        resource_requests=resource_requests,

        collaborative_notes=collaborative_notes,

        unread_count=unread_count
    )


# =========================================================
# RESOURCE REQUEST
# =========================================================

@community.route(
    "/request",
    methods=["POST"]
)
@login_required
def create_request():

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


    if not title:

        flash(
            "Please enter what resource you need.",
            "danger"
        )

        return redirect(
            url_for(
                "community.home"
            )
        )


    resource_request = ResourceRequest(

        user_id=current_user.id,

        title=title,

        description=description,

        education_level=education_level,

        course=course,

        semester=semester,

        subject=subject,

        status="open"
    )


    db.session.add(
        resource_request
    )


    # Notify admins

    admins = (
        User.query
        .filter_by(
            is_admin=True
        )
        .all()
    )


    for admin in admins:

        notification = Notification(

            user_id=admin.id,

            title="New Resource Request",

            message=(
                f"{current_user.name} requested: "
                f"{title}"
            ),

            notification_type="resource_request"
        )

        db.session.add(
            notification
        )


    db.session.commit()


    flash(
        "Resource request posted successfully.",
        "success"
    )


    return redirect(
        url_for(
            "community.home"
        )
    )


# =========================================================
# CREATE COLLABORATIVE NOTE
# =========================================================

@community.route(
    "/collaborative/create",
    methods=["POST"]
)
@login_required
def create_collaborative_note():

    title = request.form.get(
        "title",
        ""
    ).strip()

    subject = request.form.get(
        "subject",
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

    content = request.form.get(
        "content",
        ""
    ).strip()


    if not title or not subject:

        flash(
            "Title and subject are required.",
            "danger"
        )

        return redirect(
            url_for(
                "community.home"
            )
        )


    collaborative_note = CollaborativeNote(

        owner_id=current_user.id,

        title=title,

        subject=subject,

        course=course,

        semester=semester,

        content=content
    )


    db.session.add(
        collaborative_note
    )

    db.session.commit()


    flash(
        "Collaborative note created.",
        "success"
    )


    return redirect(
        url_for(
            "community.view_collaborative",
            note_id=collaborative_note.id
        )
    )


# =========================================================
# VIEW COLLABORATIVE NOTE
# =========================================================

@community.route(
    "/collaborative/<int:note_id>"
)
@login_required
def view_collaborative(note_id):

    collaborative_note = (
        CollaborativeNote.query
        .get_or_404(note_id)
    )


    contributions = (
        CollaborativeContribution.query
        .filter_by(
            collaborative_note_id=note_id
        )
        .order_by(
            CollaborativeContribution.created_at.asc()
        )
        .all()
    )


    return render_template(
        "collaborative_note.html",

        collaborative_note=collaborative_note,

        contributions=contributions
    )


# =========================================================
# ADD COLLABORATIVE CONTRIBUTION
# =========================================================

@community.route(
    "/collaborative/<int:note_id>/contribute",
    methods=["POST"]
)
@login_required
def contribute(note_id):

    collaborative_note = (
        CollaborativeNote.query
        .get_or_404(note_id)
    )


    content = request.form.get(
        "content",
        ""
    ).strip()


    if not content:

        flash(
            "Contribution cannot be empty.",
            "danger"
        )

        return redirect(
            url_for(
                "community.view_collaborative",
                note_id=note_id
            )
        )


    contribution = CollaborativeContribution(

        collaborative_note_id=note_id,

        user_id=current_user.id,

        content=content
    )


    db.session.add(
        contribution
    )


    # Notify owner when someone contributes

    if (
        collaborative_note.owner_id
        != current_user.id
    ):

        notification = Notification(

            user_id=collaborative_note.owner_id,

            title="New Collaborative Contribution",

            message=(
                f"{current_user.name} added "
                f"a contribution to "
                f"'{collaborative_note.title}'."
            ),

            notification_type="collaboration"
        )

        db.session.add(
            notification
        )


    db.session.commit()


    flash(
        "Your contribution was added.",
        "success"
    )


    return redirect(
        url_for(
            "community.view_collaborative",
            note_id=note_id
        )
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@community.route(
    "/notifications"
)
@login_required
def notifications():

    notification_list = (
        Notification.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Notification.created_at.desc()
        )
        .all()
    )


    return render_template(
        "notifications.html",

        notifications=notification_list
    )


# =========================================================
# MARK NOTIFICATION AS READ
# =========================================================

@community.route(
    "/notifications/<int:notification_id>/read"
)
@login_required
def mark_notification_read(
    notification_id
):

    notification = (
        Notification.query
        .filter_by(
            id=notification_id,
            user_id=current_user.id
        )
        .first_or_404()
    )


    notification.is_read = True

    db.session.commit()


    return redirect(
        url_for(
            "community.notifications"
        )
    )