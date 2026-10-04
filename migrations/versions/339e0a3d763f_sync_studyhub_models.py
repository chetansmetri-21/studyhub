"""sync StudyHub models

Revision ID: 339e0a3d763f
Revises: a9ac64b86443
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "339e0a3d763f"
down_revision = "a9ac64b86443"
branch_labels = None
depends_on = None


def upgrade():
    # The manually managed StudyHub tables are intentionally
    # excluded from Alembic model comparison.
    pass


def downgrade():
    pass