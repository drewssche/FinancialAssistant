from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260311_0011"
down_revision = "20260307_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("include_in_statistics", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("categories", "include_in_statistics")
