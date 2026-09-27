"""Map application accounts to Supabase identities; retain isolated seed fixtures."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("auth_provider_id", sa.String(36), nullable=True))
    op.create_unique_constraint("uq_users_auth_provider_id", "users", ["auth_provider_id"])
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.drop_constraint("uq_users_email", "users", type_="unique")


def downgrade():
    # Refuses to silently merge distinct provider identities with the same email.
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.drop_column("users", "onboarding_completed")
    op.drop_constraint("uq_users_auth_provider_id", "users", type_="unique")
    op.drop_column("users", "auth_provider_id")
