"""Keep reversible framing settings alongside the uncropped detail image.

Revision ID: 20260907_0045
Revises: 20260904_0044
"""

from alembic import op
import sqlalchemy as sa

revision = "20260907_0045"
down_revision = "20260904_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalog_media_assets", sa.Column("framing", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("catalog_media_assets", "framing")
