"""Track which reports have been conservatively assessed against consensus."""

import sqlalchemy as sa

from alembic import op

revision = "25630308138e"
down_revision = "25630308138d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "crowd_reports", sa.Column("reliability_evaluated_at", sa.DateTime(timezone=True))
    )


def downgrade():
    op.drop_column("crowd_reports", "reliability_evaluated_at")
