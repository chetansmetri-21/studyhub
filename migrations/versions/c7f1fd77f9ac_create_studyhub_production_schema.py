"""create StudyHub production schema

Revision ID: c7f1fd77f9ac
Revises: 339e0a3d763f
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa


# -------------------------------------------------------------------
# Alembic revision identifiers
# -------------------------------------------------------------------

revision = "c7f1fd77f9ac"
down_revision = "339e0a3d763f"
branch_labels = None
depends_on = None


# -------------------------------------------------------------------
# Upgrade
# -------------------------------------------------------------------

def upgrade():

    # ================================================================
    # USERS
    # ================================================================

    op.create_table(
        "users",

        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "email",
            sa.String(length=120),
            nullable=False,
        ),

        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "education_level",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "course",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "semester",
            sa.String(length=30),
            nullable=True,
        ),

        sa.Column(
            "profile_photo",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "bio",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "skills",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "interests",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "phone",
            sa.String(length=20),
            nullable=True,
        ),

        sa.Column(
            "location",
            sa.String(length=150),
            nullable=True,
        ),

        sa.Column(
            "linkedin_url",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "github_url",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "profile_updated_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.UniqueConstraint(
            "email",
            name="uq_users_email",
        ),
    )


    # ================================================================
    # NOTES
    # ================================================================

    op.create_table(
        "notes",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "education_level",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "course",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "semester",
            sa.String(length=30),
            nullable=True,
        ),

        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "uploaded_by",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_notes_uploaded_by_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "uploaded_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),

        sa.Column(
            "views",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=True,
        ),

        sa.Column(
            "downloads",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=True,
        ),

        sa.Column(
            "rating",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=True,
        ),

        sa.Column(
            "verification_status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
    )


    # ================================================================
    # PYQS
    # ================================================================

    op.create_table(
        "pyqs",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "education_level",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "course",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "semester",
            sa.String(length=30),
            nullable=True,
        ),

        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "exam_type",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "exam_year",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "exam_session",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "uploaded_by",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_pyqs_uploaded_by_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "uploaded_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),

        sa.Column(
            "views",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=True,
        ),

        sa.Column(
            "downloads",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=True,
        ),

        sa.Column(
            "extracted_text",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "parsed_questions",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "visual_analysis",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "verification_status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),

        sa.Column(
            "file_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )


    # ================================================================
    # STUDYHUB ACTIVITY
    # ================================================================

    op.create_table(
        "studyhub_activity",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "resource_type",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "resource_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "action",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_studyhub_activity_user_created",
        "studyhub_activity",
        ["user_id", "created_at"],
    )

    op.create_index(
        "ix_studyhub_activity_user_id",
        "studyhub_activity",
        ["user_id"],
    )


    # ================================================================
    # STUDYHUB BOOKMARKS
    # ================================================================

    op.create_table(
        "studyhub_bookmarks",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "resource_type",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "resource_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),

        sa.UniqueConstraint(
            "user_id",
            "resource_type",
            "resource_id",
            name="uq_studyhub_bookmark_resource",
        ),
    )

    op.create_index(
        "ix_studyhub_bookmarks_user_id",
        "studyhub_bookmarks",
        ["user_id"],
    )


    # ================================================================
    # STUDYHUB NOTIFICATIONS
    # ================================================================

    op.create_table(
        "studyhub_notifications",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "link",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_studyhub_notifications_user_id",
        "studyhub_notifications",
        ["user_id"],
    )


    # ================================================================
    # NOTE RATINGS
    # ================================================================

    op.create_table(
        "note_ratings",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "note_id",
            sa.Integer(),
            sa.ForeignKey(
                "notes.id",
                name="fk_note_ratings_note_id_notes",
            ),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_note_ratings_user_id_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "rating",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),

        sa.UniqueConstraint(
            "note_id",
            "user_id",
            name="unique_note_user_rating",
        ),
    )


    # ================================================================
    # RESOURCE REPORTS
    # ================================================================

    op.create_table(
        "resource_reports",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_resource_reports_user_id_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "resource_type",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "resource_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "reason",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),

        sa.Column(
            "reviewed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


    # ================================================================
    # RESOURCE REQUESTS
    # ================================================================

    op.create_table(
        "resource_requests",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_resource_requests_user_id_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "education_level",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "course",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "semester",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )


    # ================================================================
    # COLLABORATIVE NOTES
    # ================================================================

    op.create_table(
        "collaborative_notes",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_collaborative_notes_owner_id_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "course",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "semester",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "content",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )


    # ================================================================
    # COLLABORATIVE CONTRIBUTIONS
    # ================================================================

    op.create_table(
        "collaborative_contributions",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "collaborative_note_id",
            sa.Integer(),
            sa.ForeignKey(
                "collaborative_notes.id",
                name="fk_collaborative_contributions_note_id",
            ),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                name="fk_collaborative_contributions_user_id_users",
            ),
            nullable=False,
        ),

        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )


# -------------------------------------------------------------------
# Downgrade
# -------------------------------------------------------------------

def downgrade():

    op.drop_table("collaborative_contributions")

    op.drop_table("collaborative_notes")

    op.drop_table("resource_requests")

    op.drop_table("resource_reports")

    op.drop_table("note_ratings")

    op.drop_index(
        "ix_studyhub_notifications_user_id",
        table_name="studyhub_notifications",
    )

    op.drop_table("studyhub_notifications")

    op.drop_index(
        "ix_studyhub_bookmarks_user_id",
        table_name="studyhub_bookmarks",
    )

    op.drop_table("studyhub_bookmarks")

    op.drop_index(
        "ix_studyhub_activity_user_id",
        table_name="studyhub_activity",
    )

    op.drop_index(
        "idx_studyhub_activity_user_created",
        table_name="studyhub_activity",
    )

    op.drop_table("studyhub_activity")

    op.drop_table("pyqs")

    op.drop_table("notes")

    op.drop_table("users")