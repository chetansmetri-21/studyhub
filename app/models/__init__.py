from app import db, login_manager
from flask_login import UserMixin


# ============================================================
# USER MODEL
# ============================================================

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    education_level = db.Column(
        db.String(50),
        nullable=True
    )

    course = db.Column(
        db.String(100),
        nullable=True
    )

    semester = db.Column(
        db.String(30),
        nullable=True
    )

    # ========================================================
    # PREMIUM PROFILE INFORMATION
    # ========================================================

    profile_photo = db.Column(
        db.String(255),
        nullable=True
    )

    bio = db.Column(
        db.Text,
        nullable=True
    )

    skills = db.Column(
        db.Text,
        nullable=True
    )

    interests = db.Column(
        db.Text,
        nullable=True
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    location = db.Column(
        db.String(150),
        nullable=True
    )

    linkedin_url = db.Column(
        db.String(255),
        nullable=True
    )

    github_url = db.Column(
        db.String(255),
        nullable=True
    )

    profile_updated_at = db.Column(
        db.DateTime,
        nullable=True
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(
        int(user_id)
    )


# ============================================================
# NOTE MODEL
# ============================================================

class Note(db.Model):

    __tablename__ = "notes"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    education_level = db.Column(
        db.String(50),
        nullable=True
    )

    course = db.Column(
        db.String(100),
        nullable=True
    )

    semester = db.Column(
        db.String(30),
        nullable=True
    )

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    file_name = db.Column(
        db.String(255),
        nullable=False
    )

    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    views = db.Column(
        db.Integer,
        default=0
    )

    downloads = db.Column(
        db.Integer,
        default=0
    )

    rating = db.Column(
        db.Float,
        default=0
    )

    verification_status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )


# ============================================================
# PYQ MODEL
# ============================================================

class PYQ(db.Model):

    __tablename__ = "pyqs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    education_level = db.Column(
        db.String(50),
        nullable=False
    )

    course = db.Column(
        db.String(100),
        nullable=False
    )

    semester = db.Column(
        db.String(30),
        nullable=True
    )

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    exam_type = db.Column(
        db.String(100),
        nullable=True
    )

    exam_year = db.Column(
        db.Integer,
        nullable=False
    )

    exam_session = db.Column(
        db.String(50),
        nullable=True
    )

    file_name = db.Column(
        db.String(255),
        nullable=False
    )

    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    views = db.Column(
        db.Integer,
        default=0
    )

    downloads = db.Column(
        db.Integer,
        default=0
    )

    extracted_text = db.Column(
        db.Text,
        nullable=True
    )

    parsed_questions = db.Column(
        db.Text,
        nullable=True
    )

    visual_analysis = db.Column(
        db.Text,
        nullable=True
    )

    verification_status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )

    # ========================================================
    # SHA-256 FILE HASH
    # ========================================================

    file_hash = db.Column(
        db.String(64),
        nullable=True,
        index=True
    )

# ============================================================
# STUDYHUB ACTIVITY
# ============================================================

class Activity(db.Model):
    __tablename__ = "studyhub_activity"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )

    resource_type = db.Column(
        db.String(20),
        nullable=False
    )

    resource_id = db.Column(
        db.Integer,
        nullable=False
    )

    action = db.Column(
        db.String(30),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        nullable=False
    )

    __table_args__ = (
        db.Index(
            "idx_studyhub_activity_user_created",
            "user_id",
            "created_at"
        ),
    )


# ============================================================
# STUDYHUB BOOKMARKS
# ============================================================

class Bookmark(db.Model):
    __tablename__ = "studyhub_bookmarks"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )

    resource_type = db.Column(
        db.String(20),
        nullable=False
    )

    resource_id = db.Column(
        db.Integer,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "resource_type",
            "resource_id",
            name="uq_studyhub_bookmark_resource"
        ),
    )


# ============================================================
# STUDYHUB NOTIFICATIONS
# ============================================================

class Notification(db.Model):
    __tablename__ = "studyhub_notifications"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        nullable=False,
        index=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    link = db.Column(
        db.String(500),
        nullable=True
    )

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.text("false")
    )
    
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        nullable=False
    )


    
# ============================================================
# NOTE RATING MODEL
# ============================================================

class NoteRating(db.Model):

    __tablename__ = "note_ratings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    note_id = db.Column(
        db.Integer,
        db.ForeignKey("notes.id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    __table_args__ = (
        db.UniqueConstraint(
            "note_id",
            "user_id",
            name="unique_note_user_rating"
        ),
    )

# ============================================================
# RESOURCE REPORTS
# ============================================================

class ResourceReport(db.Model):

    __tablename__ = "resource_reports"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    resource_type = db.Column(
        db.String(20),
        nullable=False
    )

    resource_id = db.Column(
        db.Integer,
        nullable=False
    )

    reason = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True
    )

# =========================================================
# RESOURCE REQUESTS
# =========================================================

class ResourceRequest(db.Model):

    __tablename__ = "resource_requests"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    education_level = db.Column(
        db.String(50),
        nullable=True
    )

    course = db.Column(
        db.String(100),
        nullable=True
    )

    semester = db.Column(
        db.String(50),
        nullable=True
    )

    subject = db.Column(
        db.String(100),
        nullable=True
    )

    status = db.Column(
        db.String(20),
        default="open",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )



# =========================================================
# COLLABORATIVE NOTES
# =========================================================

class CollaborativeNote(db.Model):

    __tablename__ = "collaborative_notes"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    course = db.Column(
        db.String(100),
        nullable=True
    )

    semester = db.Column(
        db.String(50),
        nullable=True
    )

    content = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


# =========================================================
# COLLABORATIVE NOTE CONTRIBUTIONS
# =========================================================

class CollaborativeContribution(db.Model):

    __tablename__ = "collaborative_contributions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    collaborative_note_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "collaborative_notes.id"
        ),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )