"""Persist estimate signal summary for later analysis and public aggregates."""

import sqlalchemy as sa

from alembic import op

revision = "25630308138f"
down_revision = "25630308138e"
branch_labels = None
depends_on = None


def upgrade():
    for column in ("recent_report_count", "active_checkin_count", "recent_validation_count"):
        op.add_column(
            "occupancy_estimates",
            sa.Column(column, sa.Integer(), nullable=False, server_default="0"),
        )
    op.add_column(
        "occupancy_estimates",
        sa.Column(
            "manual_observation_used", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade():
    op.drop_column("occupancy_estimates", "manual_observation_used")
    for column in ("recent_validation_count", "active_checkin_count", "recent_report_count"):
        op.drop_column("occupancy_estimates", column)
