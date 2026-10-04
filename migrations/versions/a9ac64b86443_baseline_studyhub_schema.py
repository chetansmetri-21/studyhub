"""baseline StudyHub schema

Revision ID: a9ac64b86443
Revises:
Create Date: 2026-10-04 13:50:46.711664

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a9ac64b86443"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Existing StudyHub database tables are already created
    # by the application's ensure_tables() logic.
    #
    # This baseline migration intentionally performs no
    # destructive schema changes.
    pass


def downgrade():
    # Baseline migration intentionally performs no destructive
    # rollback operations.
    pass