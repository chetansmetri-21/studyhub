import json

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response
)

from datetime import datetime, timedelta

from flask_login import login_required, current_user
from sqlalchemy import text

from app import db, limiter
from app.models import (
    User,
    Note,
    PYQ,
    ResourceReport,
    Activity,
    Bookmark,
    Notification,
    ResourceRequest,
)


enhancements = Blueprint(
    "enhancements",
    __name__
)

# ============================================================
# ADMIN NOTES MANAGEMENT
# ============================================================

@enhancements.route("/admin/notes")
@login_required
def admin_notes():

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    notes = (
        Note.query
        .order_by(Note.uploaded_at.desc())
        .all()
    )

    total_notes = len(notes)

    approved_count = sum(
        1 for note in notes
        if note.verification_status == "approved"
    )

    pending_count = sum(
        1 for note in notes
        if note.verification_status == "pending"
    )

    rejected_count = sum(
        1 for note in notes
        if note.verification_status == "rejected"
    )

    # Get uploader names
    uploader_ids = {
        note.uploaded_by
        for note in notes
        if note.uploaded_by
    }

    users = (
        User.query
        .filter(User.id.in_(uploader_ids))
        .all()
        if uploader_ids
        else []
    )

    uploader_map = {
        user.id: user
        for user in users
    }

    return render_template(
        "admin_notes.html",
        notes=notes,
        total_notes=total_notes,
        approved_count=approved_count,
        pending_count=pending_count,
        rejected_count=rejected_count,
        uploader_map=uploader_map
    )


# ============================================================
# APPROVE NOTE
# ============================================================

@enhancements.route(
    "/admin/notes/<int:note_id>/approve",
    methods=["POST"]
)
@login_required
def admin_approve_note(note_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    note = Note.query.get_or_404(note_id)

    note.verification_status = "approved"

    db.session.commit()

    flash(
        f'"{note.title}" has been approved.',
        "success"
    )

    return redirect(
        url_for("enhancements.admin_notes")
    )


# ============================================================
# REJECT NOTE
# ============================================================

@enhancements.route(
    "/admin/notes/<int:note_id>/reject",
    methods=["POST"]
)
@login_required
def admin_reject_note(note_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    note = Note.query.get_or_404(note_id)

    note.verification_status = "rejected"

    db.session.commit()

    flash(
        f'"{note.title}" has been rejected.',
        "warning"
    )

    return redirect(
        url_for("enhancements.admin_notes")
    )


# ============================================================
# DELETE NOTE
# ============================================================

@enhancements.route(
    "/admin/notes/<int:note_id>/delete",
    methods=["POST"]
)
@login_required
def admin_delete_note(note_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    note = Note.query.get_or_404(note_id)

    title = note.title

    db.session.delete(note)
    db.session.commit()

    flash(
        f'"{title}" has been deleted.',
        "success"
    )

    return redirect(
        url_for("enhancements.admin_notes")
    )



# =========================================================
# DATABASE SETUP
# =========================================================

def ensure_tables():

    
    # =====================================================
    # RESOURCE REPORTS / MODERATION
    # =====================================================

    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS resource_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            resource_type VARCHAR(20) NOT NULL,
            resource_id INTEGER NOT NULL,
            reason VARCHAR(100) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reviewed_at DATETIME
        )
    """))

    db.session.commit()

@enhancements.before_app_request
def setup_tables():

    try:
        ensure_tables()
    except Exception:
        db.session.rollback()


# =========================================================
# BOOKMARK HELPERS
# =========================================================

def get_bookmark_ids(resource_type):

    rows = db.session.execute(
        text("""
            SELECT resource_id
            FROM studyhub_bookmarks
            WHERE user_id = :user_id
            AND resource_type = :resource_type
        """),
        {
            "user_id": current_user.id,
            "resource_type": resource_type
        }
    ).fetchall()

    return {row[0] for row in rows}


@enhancements.app_context_processor
def bookmark_context():

    if not current_user.is_authenticated:
        return {
            "sh_bookmarked_note_ids": [],
            "sh_bookmarked_pyq_ids": []
        }

    try:
        return {
            "sh_bookmarked_note_ids":
                list(get_bookmark_ids("note")),

            "sh_bookmarked_pyq_ids":
                list(get_bookmark_ids("pyq"))
        }

    except Exception:
        return {
            "sh_bookmarked_note_ids": [],
            "sh_bookmarked_pyq_ids": []
        }


# =========================================================
# STUDYHUB MANIFEST
# =========================================================

@enhancements.route("/studyhub-manifest.json")
def studyhub_manifest():

    return jsonify({
        "name": "StudyHub",
        "short_name": "StudyHub",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#4f46e5",
        "description":
            "Student notes, PYQs and academic intelligence platform."
    })


# =========================================================
# SERVICE WORKER
# =========================================================

@enhancements.route("/studyhub-sw.js")
def studyhub_service_worker():

    script = """
const CACHE_NAME = "studyhub-v1";

self.addEventListener("install", event => {

    event.waitUntil(
        caches.open(CACHE_NAME)
    );

    self.skipWaiting();
});


self.addEventListener("activate", event => {

    event.waitUntil(
        self.clients.claim()
    );

});


self.addEventListener("fetch", event => {

    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(

        fetch(event.request)

            .then(response => {

                const copy = response.clone();

                caches.open(CACHE_NAME)
                    .then(cache => {
                        cache.put(
                            event.request,
                            copy
                        );
                    });

                return response;
            })

            .catch(() => {
                return caches.match(
                    event.request
                );
            })

    );

});
"""

    return Response(
        script,
        mimetype="application/javascript"
    )


# =========================================================
# TOGGLE BOOKMARK
# =========================================================

@enhancements.route(
    "/bookmark/toggle",
    methods=["POST"]
)
@login_required
def toggle_bookmark():

    resource_type = (
        request.form
        .get("resource_type", "")
        .strip()
        .lower()
    )

    try:
        resource_id = int(
            request.form.get(
                "resource_id",
                0
            )
        )
    except ValueError:
        resource_id = 0


    if resource_type not in {
        "note",
        "pyq"
    } or resource_id <= 0:

        return jsonify({
            "ok": False,
            "message": "Invalid resource."
        }), 400


    if resource_type == "note":

        resource = Note.query.filter(
            Note.id == resource_id
        ).first()

    else:

        resource = PYQ.query.filter(
            PYQ.id == resource_id
        ).first()


    if not resource:

        return jsonify({
            "ok": False,
            "message": "Resource not found."
        }), 404


    existing = db.session.execute(
        text("""
            SELECT id
            FROM studyhub_bookmarks
            WHERE user_id = :user_id
            AND resource_type = :resource_type
            AND resource_id = :resource_id
        """),
        {
            "user_id": current_user.id,
            "resource_type": resource_type,
            "resource_id": resource_id
        }
    ).first()


    if existing:

        db.session.execute(
            text("""
                DELETE FROM studyhub_bookmarks
                WHERE id = :id
            """),
            {
                "id": existing[0]
            }
        )

        saved = False

    else:

        db.session.execute(
            text("""
                INSERT INTO studyhub_bookmarks
                (
                    user_id,
                    resource_type,
                    resource_id
                )
                VALUES
                (
                    :user_id,
                    :resource_type,
                    :resource_id
                )
            """),
            {
                "user_id": current_user.id,
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )

        saved = True


    db.session.commit()


    return jsonify({
        "ok": True,
        "saved": saved
    })


# =========================================================
# BOOKMARKS PAGE
# =========================================================

@enhancements.route("/bookmarks")
@login_required
def bookmarks():

    note_ids = get_bookmark_ids("note")
    pyq_ids = get_bookmark_ids("pyq")


    notes = []

    pyqs = []


    if note_ids:

        notes = (
            Note.query
            .filter(
                Note.id.in_(note_ids)
            )
            .all()
        )


    if pyq_ids:

        pyqs = (
            PYQ.query
            .filter(
                PYQ.id.in_(pyq_ids)
            )
            .all()
        )


    return render_template(
        "studyhub_bookmarks.html",
        notes=notes,
        pyqs=pyqs
    )

# ============================================================
# PREMIUM DASHBOARD ANALYTICS
# ============================================================

@enhancements.route("/dashboard/analytics")
@login_required
def dashboard_analytics():

    user_id = current_user.id

    # --------------------------------------------------------
    # BOOKMARKS
    # --------------------------------------------------------

    bookmarks = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_bookmarks
            WHERE user_id = :user_id
        """),
        {
            "user_id": user_id
        }
    ).scalar() or 0

    # --------------------------------------------------------
    # ACTIVITY COUNTS
    # --------------------------------------------------------

    activity_total = 0
    viewed_total = 0
    downloaded_total = 0

    try:

        activity_total = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM studyhub_activity
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id
            }
        ).scalar() or 0

        viewed_total = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM studyhub_activity
                WHERE user_id = :user_id
                AND action = 'viewed'
            """),
            {
                "user_id": user_id
            }
        ).scalar() or 0

        downloaded_total = db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM studyhub_activity
                WHERE user_id = :user_id
                AND action = 'downloaded'
            """),
            {
                "user_id": user_id
            }
        ).scalar() or 0

    except Exception:
        pass

    # --------------------------------------------------------
    # USER UPLOADS
    # --------------------------------------------------------

    uploaded_notes = Note.query.filter(
        Note.uploaded_by == user_id
    ).count()

    uploaded_pyqs = PYQ.query.filter(
        PYQ.uploaded_by == user_id
    ).count()

    # --------------------------------------------------------
    # RECENT ACTIVITY
    # --------------------------------------------------------

    recent_activity = []

    try:

        rows = db.session.execute(
            text("""
                SELECT
                    resource_type,
                    resource_id,
                    action,
                    created_at
                FROM studyhub_activity
                WHERE user_id = :user_id
                ORDER BY id DESC
                LIMIT 5
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()

        for row in rows:

            title = "Study Resource"
            resource_url = "#"

            if row["resource_type"] == "note":

                resource = Note.query.filter(
                    Note.id == row["resource_id"]
                ).first()

                if resource:

                    title = resource.title

                    try:
                        resource_url = url_for(
                            "notes.view_note",
                            note_id=resource.id
                        )
                    except Exception:
                        resource_url = "#"

            elif row["resource_type"] == "pyq":

                resource = PYQ.query.filter(
                    PYQ.id == row["resource_id"]
                ).first()

                if resource:

                    title = resource.title

                    try:
                        resource_url = url_for(
                            "pyq.preview_pyq",
                            pyq_id=resource.id
                        )
                    except Exception:
                        resource_url = "#"

            recent_activity.append({
                "resource_type": row["resource_type"],
                "action": row["action"],
                "title": title,
                "url": resource_url,
                "created_at": str(
                    row["created_at"]
                )
            })

    except Exception:
        recent_activity = []

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return jsonify({
        "ok": True,

        "analytics": {
            "bookmarks": bookmarks,
            "activity_total": activity_total,
            "viewed": viewed_total,
            "downloads": downloaded_total,
            "uploaded_notes": uploaded_notes,
            "uploaded_pyqs": uploaded_pyqs
        },

        "recent_activity": recent_activity
    })

# =========================================================
# ACTIVITY & HISTORY
# =========================================================

@enhancements.route("/activity")
@login_required
def activity():

    selected_filter = (
        request.args
        .get("filter", "all")
        .strip()
        .lower()
    )

    allowed_filters = {
        "all",
        "viewed",
        "downloaded"
    }

    if selected_filter not in allowed_filters:
        selected_filter = "all"


    # -----------------------------------------------------
    # ACTIVITY QUERY
    # -----------------------------------------------------

    query = """
        SELECT
            id,
            resource_type,
            resource_id,
            action,
            created_at
        FROM studyhub_activity
        WHERE user_id = :user_id
    """

    params = {
        "user_id": current_user.id
    }


    if selected_filter == "viewed":

        query += """
            AND action = 'viewed'
        """

    elif selected_filter == "downloaded":

        query += """
            AND action = 'downloaded'
        """


    query += """
        ORDER BY id DESC
        LIMIT 100
    """


    rows = db.session.execute(
        text(query),
        params
    ).mappings().all()


    # -----------------------------------------------------
    # BUILD RESOURCE DATA
    # -----------------------------------------------------

    activities = []

    for row in rows:

        resource = None

        if row["resource_type"] == "note":

            resource = (
                Note.query
                .filter(
                    Note.id == row["resource_id"]
                )
                .first()
            )

        elif row["resource_type"] == "pyq":

            resource = (
                PYQ.query
                .filter(
                    PYQ.id == row["resource_id"]
                )
                .first()
            )


        # Resource may have been deleted later.
        if not resource:
            continue


        if row["resource_type"] == "note":

            resource_url = url_for(
                "notes.view_note",
                note_id=resource.id
            )

            title = resource.title

            subtitle = (
                resource.subject
                or resource.course
                or "Study Note"
            )

            icon = "📚"

        else:

            resource_url = url_for(
                "pyq.preview_pyq",
                pyq_id=resource.id
            )

            title = resource.title

            subtitle = (
                resource.subject
                or resource.course
                or "Previous Year Paper"
            )

            icon = "📝"


        activities.append({
            "id": row["id"],
            "resource_type":
                row["resource_type"],
            "resource_id":
                row["resource_id"],
            "action":
                row["action"],
            "created_at":
                row["created_at"],
            "resource_url":
                resource_url,
            "title":
                title,
            "subtitle":
                subtitle,
            "icon":
                icon
        })


    # -----------------------------------------------------
    # PERSONAL STATISTICS
    # -----------------------------------------------------

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


    viewed_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_activity
            WHERE user_id = :user_id
            AND action = 'viewed'
        """),
        {
            "user_id": current_user.id
        }
    ).scalar() or 0


    downloaded_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_activity
            WHERE user_id = :user_id
            AND action = 'downloaded'
        """),
        {
            "user_id": current_user.id
        }
    ).scalar() or 0


    bookmarked_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_bookmarks
            WHERE user_id = :user_id
        """),
        {
            "user_id": current_user.id
        }
    ).scalar() or 0


    return render_template(
        "activity.html",
        activities=activities,
        selected_filter=selected_filter,
        total_activity=total_activity,
        viewed_count=viewed_count,
        downloaded_count=downloaded_count,
        bookmarked_count=bookmarked_count
    )


# =========================================================
# LOG ACTIVITY
# =========================================================

@enhancements.route(
    "/activity/log",
    methods=["POST"]
)
@login_required
def log_activity():

    resource_type = (
        request.form
        .get("resource_type", "")
        .strip()
        .lower()
    )

    action = (
        request.form
        .get("action", "")
        .strip()
        .lower()
    )


    try:

        resource_id = int(
            request.form.get(
                "resource_id",
                0
            )
        )

    except (TypeError, ValueError):

        resource_id = 0


    if resource_type not in {
        "note",
        "pyq"
    }:

        return jsonify({
            "ok": False,
            "message": "Invalid resource type."
        }), 400


    if action not in {
        "viewed",
        "downloaded"
    }:

        return jsonify({
            "ok": False,
            "message": "Invalid activity."
        }), 400


    if resource_id <= 0:

        return jsonify({
            "ok": False,
            "message": "Invalid resource."
        }), 400


    # -----------------------------------------------------
    # VERIFY RESOURCE EXISTS
    # -----------------------------------------------------

    if resource_type == "note":

        resource = (
            Note.query
            .filter(
                Note.id == resource_id
            )
            .first()
        )

    else:

        resource = (
            PYQ.query
            .filter(
                PYQ.id == resource_id
            )
            .first()
        )


    if not resource:

        return jsonify({
            "ok": False,
            "message": "Resource not found."
        }), 404


    # -----------------------------------------------------
    # AVOID RAPID DUPLICATES
    # -----------------------------------------------------

    five_seconds_ago = datetime.utcnow() - timedelta(seconds=5)

    duplicate = Activity.query.filter(
        Activity.user_id == current_user.id,
        Activity.resource_type == resource_type,
        Activity.resource_id == resource_id,
        Activity.action == action,
        Activity.created_at >= five_seconds_ago
    ).first()


    if not duplicate:

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
                    :resource_type,
                    :resource_id,
                    :action
                )
            """),
            {
                "user_id":
                    current_user.id,

                "resource_type":
                    resource_type,

                "resource_id":
                    resource_id,

                "action":
                    action
            }
        )

        db.session.commit()


    return jsonify({
        "ok": True
    })


# =========================================================
# CLEAR ACTIVITY HISTORY
# =========================================================

@enhancements.route(
    "/activity/clear",
    methods=["POST"]
)
@login_required
def clear_activity():

    db.session.execute(
        text("""
            DELETE FROM studyhub_activity
            WHERE user_id = :user_id
        """),
        {
            "user_id": current_user.id
        }
    )

    db.session.commit()


    flash(
        "Your activity history has been cleared.",
        "success"
    )


    return redirect(
        url_for(
            "enhancements.activity"
        )
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@enhancements.route("/notifications")
@login_required
def notifications():

    rows = db.session.execute(
        text("""
            SELECT
                id,
                title,
                message,
                link,
                is_read,
                created_at
            FROM studyhub_notifications
            WHERE user_id = :user_id
            ORDER BY id DESC
            LIMIT 100
        """),
        {
            "user_id": current_user.id
        }
    ).mappings().all()


    return render_template(
        "studyhub_notifications.html",
        notifications=rows
    )


# =========================================================
# MARK NOTIFICATION READ
# =========================================================

@enhancements.route(
    "/notifications/read/<int:notification_id>",
    methods=["POST"]
)
@login_required
def mark_notification_read(
    notification_id
):

    db.session.execute(
        text("""
            UPDATE studyhub_notifications
            SET is_read = 1
            WHERE id = :notification_id
            AND user_id = :user_id
        """),
        {
            "notification_id":
                notification_id,

            "user_id":
                current_user.id
        }
    )

    db.session.commit()


    return jsonify({
        "ok": True
    })


# =========================================================
# PREPARE SMART
# =========================================================

@enhancements.route("/prepare-smart")
@login_required
def prepare_smart():

    from app.utils.question_parser import (
        parse_questions
    )

    from app.utils.question_analyzer import (
        group_similar_questions,
        get_group_topic
    )


    papers = (
        PYQ.query
        .order_by(
            PYQ.exam_year.asc(),
            PYQ.id.asc()
        )
        .all()
    )


    questions = []
    metadata = []


    for paper in papers:

        parsed = []


        raw_questions = getattr(
            paper,
            "parsed_questions",
            None
        )


        if raw_questions:

            try:

                parsed = (
                    json.loads(raw_questions)
                    if isinstance(
                        raw_questions,
                        str
                    )
                    else raw_questions
                )

            except Exception:

                parsed = []


        if (
            not parsed
            and getattr(
                paper,
                "extracted_text",
                None
            )
        ):

            try:

                parsed = (
                    parse_questions(
                        paper.extracted_text
                    )
                    or []
                )

            except Exception:

                parsed = []


        for item in parsed:

            if isinstance(item, dict):

                question_text = (
                    item.get("question")
                    or item.get("text")
                    or item.get("question_text")
                )

            else:

                question_text = str(item)


            if not question_text:
                continue


            question_text = (
                question_text.strip()
            )


            if len(question_text) < 10:
                continue


            questions.append(
                question_text
            )


            metadata.append({

                "paper_id":
                    paper.id,

                "year":
                    paper.exam_year,

                "session":
                    getattr(
                        paper,
                        "exam_session",
                        ""
                    ),

                "subject":
                    getattr(
                        paper,
                        "subject",
                        ""
                    ),

                "question":
                    question_text
            })


    repeated_questions = []


    if questions:

        groups = group_similar_questions(
            questions,
            threshold=0.45
        )

    else:

        groups = []


    years = [
        paper.exam_year
        for paper in papers
        if paper.exam_year
    ]


    latest_year = (
        max(years)
        if years
        else None
    )


    for group in groups:

        appearances = []


        for question in group:

            for index, original in enumerate(
                questions
            ):

                if original == question:

                    appearances.append(
                        metadata[index]
                    )


        paper_ids = {
            item["paper_id"]
            for item in appearances
        }


        if len(paper_ids) < 2:
            continue


        appearance_years = sorted(
            {
                item["year"]
                for item in appearances
                if item["year"]
            },
            reverse=True
        )


        if not appearance_years:
            continue


        latest_appearance = (
            appearance_years[0]
        )


        if (
            latest_year
            and latest_appearance == latest_year
        ):
            continue


        try:

            topic = (
                get_group_topic(group)
                or "General Topic"
            )

        except Exception:

            topic = "General Topic"


        count = len(paper_ids)


        repeated_questions.append({

            "question":
                group[0],

            "topic":
                topic,

            "count":
                count,

            "years":
                appearance_years,

            "priority":
                (
                    "High Priority"
                    if count >= 3
                    else "Review Soon"
                )

        })


    repeated_questions.sort(
        key=lambda item: (
            -item["count"],
            -(item["years"][0]
              if item["years"]
              else 0)
        )
    )


    return render_template(
        "prepare_smart.html",

        smart_questions=
            repeated_questions[:30],

        latest_year=
            latest_year,

        paper_count=
            len(papers),

        question_count=
            len(questions)
    )


# =========================================================
# ADMIN ANALYTICS
# =========================================================

@enhancements.route(
    "/admin/analytics"
)
@login_required
def admin_analytics():

    if not getattr(
        current_user,
        "is_admin",
        False
    ):

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for(
                "student.dashboard"
            )
        )


    user_count = db.session.execute(
        text(
            "SELECT COUNT(*) FROM users"
        )
    ).scalar() or 0


    note_count = Note.query.count()
    pyq_count = PYQ.query.count()


    approved_notes = (
        Note.query
        .filter(
            Note.verification_status ==
            "approved"
        )
        .count()
        if hasattr(
            Note,
            "verification_status"
        )
        else note_count
    )


    approved_pyqs = (
        PYQ.query
        .filter(
            PYQ.verification_status ==
            "approved"
        )
        .count()
        if hasattr(
            PYQ,
            "verification_status"
        )
        else pyq_count
    )


    bookmark_count = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_bookmarks
        """)
    ).scalar() or 0


    unread_notifications = (
        db.session.execute(
            text("""
                SELECT COUNT(*)
                FROM studyhub_notifications
                WHERE is_read = 0
            """)
        ).scalar()
        or 0
    )

    # Pending moderation reports
    pending_reports = ResourceReport.query.filter_by(
        status="pending"
    ).count()


    return render_template(
        "admin_analytics.html",

        user_count=user_count,

        note_count=note_count,

        pyq_count=pyq_count,

        approved_notes=
            approved_notes,

        approved_pyqs=
            approved_pyqs,

        total_views=0,

        total_downloads=0,

        bookmarks_count=
            bookmark_count,

        unread_count=
            unread_notifications,

        pending_reports=
            pending_reports
            
    )

# ============================================================
# ADMIN PYQ MANAGEMENT
# ============================================================

@enhancements.route("/admin/pyqs")
@login_required
def admin_pyqs():

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    pyqs = PYQ.query.order_by(
        PYQ.id.desc()
    ).all()

    return render_template(
        "admin_pyqs.html",
        pyqs=pyqs
    )


# ============================================================
# ADMIN EDIT PYQ SUBJECT
# ============================================================

@enhancements.route(
    "/admin/pyqs/<int:pyq_id>/edit",
    methods=["POST"]
)
@login_required
def admin_edit_pyq_subject(pyq_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    pyq_item = PYQ.query.get_or_404(pyq_id)

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    if not subject:
        flash(
            "Subject cannot be empty.",
            "error"
        )

        return redirect(
            url_for("enhancements.admin_pyqs")
        )

    pyq_item.subject = subject

    db.session.commit()

    flash(
        "PYQ subject updated successfully.",
        "success"
    )

    return redirect(
        url_for("enhancements.admin_pyqs")
    )
# ============================================================
# ADMIN REPORT MANAGEMENT
# ============================================================

@enhancements.route("/admin/reports")
@login_required
def admin_reports():

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(
            url_for("student.dashboard")
        )

    reports = ResourceReport.query.order_by(
        ResourceReport.id.desc()
    ).all()

    pending_count = ResourceReport.query.filter_by(
        status="pending"
    ).count()

    return render_template(
        "admin_reports.html",
        reports=reports,
        pending_count=pending_count
    )


# ============================================================
# UPDATE REPORT STATUS
# ============================================================

@enhancements.route(
    "/admin/reports/<int:report_id>/status",
    methods=["POST"]
)
@login_required
def admin_update_report_status(report_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(
            url_for("student.dashboard")
        )

    report = ResourceReport.query.get_or_404(
        report_id
    )

    status = request.form.get(
        "status",
        ""
    ).strip().lower()

    allowed_statuses = {
        "pending",
        "reviewed",
        "resolved",
        "dismissed"
    }

    if status not in allowed_statuses:

        flash(
            "Invalid report status.",
            "error"
        )

        return redirect(
            url_for("enhancements.admin_reports")
        )

    report.status = status

    if status in {
        "reviewed",
        "resolved",
        "dismissed"
    }:
        report.reviewed_at = db.func.current_timestamp()

    else:
        report.reviewed_at = None

    db.session.commit()

    flash(
        "Report status updated successfully.",
        "success"
    )

    return redirect(
        url_for("enhancements.admin_reports")
    )
# ============================================================
# ADMIN USER MANAGEMENT
# ============================================================

@enhancements.route("/admin/users")
@login_required
def admin_users():

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    users = User.query.order_by(User.id.desc()).all()

    total_users = len(users)

    admin_users_count = sum(
        1 for user in users
        if getattr(user, "is_admin", False)
    )

    student_users_count = total_users - admin_users_count

    return render_template(
        "admin_users.html",
        users=users,
        total_users=total_users,
        admin_users_count=admin_users_count,
        student_users_count=student_users_count
    )


# ============================================================
# PROMOTE USER TO ADMIN
# ============================================================

@enhancements.route(
    "/admin/users/<int:user_id>/make-admin",
    methods=["POST"]
)
@login_required
def admin_make_user_admin(user_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    user = User.query.get_or_404(user_id)

    user.is_admin = True

    db.session.commit()

    flash(
        f"{user.name} is now an admin.",
        "success"
    )

    return redirect(
        url_for("enhancements.admin_users")
    )


# ============================================================
# REMOVE ADMIN ACCESS
# ============================================================

@enhancements.route(
    "/admin/users/<int:user_id>/remove-admin",
    methods=["POST"]
)
@login_required
def admin_remove_user_admin(user_id):

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(url_for("student.dashboard"))

    user = User.query.get_or_404(user_id)

    # Prevent admin from removing their own admin access
    if user.id == current_user.id:

        flash(
            "You cannot remove your own admin access.",
            "warning"
        )

        return redirect(
            url_for("enhancements.admin_users")
        )

    user.is_admin = False

    db.session.commit()

    flash(
        f"Admin access removed from {user.name}.",
        "success"
    )

    return redirect(
        url_for("enhancements.admin_users")
    )

# ============================================================
# ADMIN NOTIFICATION MANAGEMENT
# ============================================================

@enhancements.route("/admin/notifications")
@login_required
def admin_notifications():

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(
            url_for("student.dashboard")
        )

    users = User.query.order_by(
        User.name.asc()
    ).all()

    total_users = len(users)

    total_notifications = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_notifications
        """)
    ).scalar() or 0

    unread_notifications = db.session.execute(
        text("""
            SELECT COUNT(*)
            FROM studyhub_notifications
            WHERE is_read = 0
        """)
    ).scalar() or 0

    return render_template(
        "admin_notifications.html",
        users=users,
        total_users=total_users,
        total_notifications=total_notifications,
        unread_notifications=unread_notifications
    )


# ============================================================
# SEND NOTIFICATION
# ============================================================

@enhancements.route(
    "/admin/notifications/send",
    methods=["POST"]
)
@login_required
def admin_send_notification():

    if not getattr(current_user, "is_admin", False):
        flash("Admin access required.", "error")
        return redirect(
            url_for("student.dashboard")
        )

    title = request.form.get(
        "title",
        ""
    ).strip()

    message = request.form.get(
        "message",
        ""
    ).strip()

    link = request.form.get(
        "link",
        ""
    ).strip()

    recipient_type = request.form.get(
        "recipient_type",
        "all"
    ).strip()

    if not title:
        flash(
            "Notification title is required.",
            "error"
        )
        return redirect(
            url_for("enhancements.admin_notifications")
        )

    if not message:
        flash(
            "Notification message is required.",
            "error"
        )
        return redirect(
            url_for("enhancements.admin_notifications")
        )

    # --------------------------------------------------------
    # SELECT RECIPIENTS
    # --------------------------------------------------------

    if recipient_type == "all":

        users = User.query.order_by(
            User.id.asc()
        ).all()

    else:

        try:
            selected_user_id = int(
                request.form.get(
                    "user_id",
                    0
                )
            )
        except ValueError:
            selected_user_id = 0

        if selected_user_id <= 0:

            flash(
                "Please select a valid user.",
                "error"
            )

            return redirect(
                url_for(
                    "enhancements.admin_notifications"
                )
            )

        user = User.query.get(
            selected_user_id
        )

        if not user:

            flash(
                "Selected user was not found.",
                "error"
            )

            return redirect(
                url_for(
                    "enhancements.admin_notifications"
                )
            )

        users = [user]

    # --------------------------------------------------------
    # CREATE NOTIFICATIONS
    # --------------------------------------------------------

    for user in users:

        db.session.execute(
            text("""
                INSERT INTO studyhub_notifications
                (
                    user_id,
                    title,
                    message,
                    link,
                    is_read
                )
                VALUES
                (
                    :user_id,
                    :title,
                    :message,
                    :link,
                    0
                )
            """),
            {
                "user_id": user.id,
                "title": title,
                "message": message,
                "link": link or None
            }
        )

    db.session.commit()

    recipient_count = len(users)

    flash(
        f"Notification sent successfully to "
        f"{recipient_count} user"
        f"{'s' if recipient_count != 1 else ''}.",
        "success"
    )

    return redirect(
        url_for(
            "enhancements.admin_notifications"
        )
    )


# ============================================================
# DELETE NOTIFICATION
# ============================================================

@enhancements.route(
    "/admin/notifications/<int:notification_id>/delete",
    methods=["POST"]
)
@login_required
def admin_delete_notification(
    notification_id
):

    if not getattr(current_user, "is_admin", False):
        flash(
            "Admin access required.",
            "error"
        )
        return redirect(
            url_for("student.dashboard")
        )

    result = db.session.execute(
        text("""
            DELETE FROM studyhub_notifications
            WHERE id = :notification_id
        """),
        {
            "notification_id":
                notification_id
        }
    )

    db.session.commit()

    if result.rowcount:
        flash(
            "Notification deleted successfully.",
            "success"
        )
    else:
        flash(
            "Notification not found.",
            "warning"
        )

    return redirect(
        url_for(
            "enhancements.admin_notifications"
        )
    )
# ============================================================
# RESOURCE REQUESTS
# ============================================================

@enhancements.route("/resource-requests")
@login_required
def resource_requests():

    requests = (
        ResourceRequest.query
        .filter_by(user_id=current_user.id)
        .order_by(
            ResourceRequest.id.desc()
        )
        .all()
    )

    return render_template(
        "resource_requests.html",
        requests=requests
    )


# ============================================================
# CREATE RESOURCE REQUEST
# ============================================================

@enhancements.route(
    "/resource-requests/create",
    methods=["POST"]
)
@login_required
@limiter.limit("5 per hour")
def create_resource_request():

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
            "error"
        )

        return redirect(
            url_for(
                "enhancements.resource_requests"
            )
        )

    resource_request = ResourceRequest(

        user_id=current_user.id,

        title=title,

        description=description or None,

        education_level=
            education_level or None,

        course=
            course or None,

        semester=
            semester or None,

        subject=
            subject or None,

        status="open"
    )

    db.session.add(
        resource_request
    )

    db.session.commit()

    # Notify admin users
    admins = User.query.filter_by(
        is_admin=True
    ).all()

    for admin in admins:

        db.session.execute(
            text("""
                INSERT INTO studyhub_notifications
                (
                    user_id,
                    title,
                    message,
                    link,
                    is_read
                )
                VALUES
                (
                    :user_id,
                    :title,
                    :message,
                    :link,
                    0
                )
            """),
            {
                "user_id": admin.id,

                "title":
                    "New Resource Request",

                "message":
                    f"{current_user.name} requested: {title}",

                "link":
                    "/admin/resource-requests"
            }
        )

    db.session.commit()

    flash(
        "Your resource request has been submitted.",
        "success"
    )

    return redirect(
        url_for(
            "enhancements.resource_requests"
        )
    )


# ============================================================
# ADMIN RESOURCE REQUESTS
# ============================================================

@enhancements.route(
    "/admin/resource-requests"
)
@login_required
def admin_resource_requests():

    if not getattr(
        current_user,
        "is_admin",
        False
    ):

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for(
                "student.dashboard"
            )
        )

    requests = (
        ResourceRequest.query
        .order_by(
            ResourceRequest.id.desc()
        )
        .all()
    )

    total_requests = len(
        requests
    )

    open_requests = sum(
        1
        for item in requests
        if item.status == "open"
    )

    progress_requests = sum(
        1
        for item in requests
        if item.status == "in_progress"
    )

    fulfilled_requests = sum(
        1
        for item in requests
        if item.status == "fulfilled"
    )

    rejected_requests = sum(
        1
        for item in requests
        if item.status == "rejected"
    )

    users = {
        user.id: user
        for user in User.query.all()
    }

    return render_template(
        "admin_resource_requests.html",

        requests=requests,

        users=users,

        total_requests=
            total_requests,

        open_requests=
            open_requests,

        progress_requests=
            progress_requests,

        fulfilled_requests=
            fulfilled_requests,

        rejected_requests=
            rejected_requests
    )


# ============================================================
# ADMIN UPDATE RESOURCE REQUEST STATUS
# ============================================================

@enhancements.route(
    "/admin/resource-requests/<int:request_id>/status",
    methods=["POST"]
)
@login_required
def admin_update_resource_request(
    request_id
):

    if not getattr(
        current_user,
        "is_admin",
        False
    ):

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for(
                "student.dashboard"
            )
        )

    resource_request = (
        ResourceRequest.query
        .get_or_404(request_id)
    )

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    allowed_statuses = {
        "open",
        "in_progress",
        "fulfilled",
        "rejected"
    }

    if new_status not in allowed_statuses:

        flash(
            "Invalid request status.",
            "error"
        )

        return redirect(
            url_for(
                "enhancements.admin_resource_requests"
            )
        )

    resource_request.status = new_status

    db.session.commit()

    # Notify requester
    status_names = {
        "open": "Open",
        "in_progress": "In Progress",
        "fulfilled": "Fulfilled",
        "rejected": "Rejected"
    }

    db.session.execute(
        text("""
            INSERT INTO studyhub_notifications
            (
                user_id,
                title,
                message,
                link,
                is_read
            )
            VALUES
            (
                :user_id,
                :title,
                :message,
                :link,
                0
            )
        """),
        {
            "user_id":
                resource_request.user_id,

            "title":
                "Resource Request Updated",

            "message":
                (
                    f"Your request "
                    f"'{resource_request.title}' "
                    f"is now "
                    f"{status_names[new_status]}."
                ),

            "link":
                "/resource-requests"
        }
    )

    db.session.commit()

    flash(
        "Resource request status updated.",
        "success"
    )

    return redirect(
        url_for(
            "enhancements.admin_resource_requests"
        )
    )


# ============================================================
# ADMIN DELETE RESOURCE REQUEST
# ============================================================

@enhancements.route(
    "/admin/resource-requests/<int:request_id>/delete",
    methods=["POST"]
)
@login_required
def admin_delete_resource_request(
    request_id
):

    if not getattr(
        current_user,
        "is_admin",
        False
    ):

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for(
                "student.dashboard"
            )
        )

    resource_request = (
        ResourceRequest.query
        .get_or_404(request_id)
    )

    db.session.delete(
        resource_request
    )

    db.session.commit()

    flash(
        "Resource request deleted.",
        "success"
    )

    return redirect(
        url_for(
            "enhancements.admin_resource_requests"
        )
    )