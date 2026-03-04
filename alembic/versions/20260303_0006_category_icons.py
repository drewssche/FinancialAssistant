"""add icon field to categories

Revision ID: 20260303_0006
Revises: 20260303_0005
Create Date: 2026-03-03 23:55:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_0006"
down_revision = "20260303_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("categories")}
    if "icon" not in columns:
        op.add_column("categories", sa.Column("icon", sa.String(length=16), nullable=False, server_default=""))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {col["name"] for col in inspector.get_columns("categories")}
    if "icon" in columns:
        op.drop_column("categories", "icon")
