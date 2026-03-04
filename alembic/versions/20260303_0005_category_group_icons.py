"""add icon field to category groups

Revision ID: 20260303_0005
Revises: 20260303_0004
Create Date: 2026-03-03 23:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_0005"
down_revision = "20260303_0004"
branch_labels = None
depends_on = None

GROUP_ICON_SEED = {
    ("income", "Основной доход"): "💼",
    ("income", "Прочие поступления"): "✨",
    ("expense", "Базовые платежи"): "🏠",
    ("expense", "Еда"): "🍽️",
    ("expense", "Здоровье и уход"): "💊",
    ("expense", "Покупки и сервис"): "🛍️",
    ("expense", "Досуг"): "🎉",
    ("expense", "Подарки и форс-мажоры"): "🎁",
}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    category_group_columns = {col["name"] for col in inspector.get_columns("category_groups")}
    if "icon" not in category_group_columns:
        op.add_column(
            "category_groups",
            sa.Column("icon", sa.String(length=16), nullable=False, server_default="📁"),
        )

    for (kind, name), icon in GROUP_ICON_SEED.items():
        conn.execute(
            sa.text(
                """
                UPDATE category_groups
                SET icon=:icon
                WHERE kind=:kind AND name=:name
                """
            ),
            {"icon": icon, "kind": kind, "name": name},
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    category_group_columns = {col["name"] for col in inspector.get_columns("category_groups")}
    if "icon" in category_group_columns:
        op.drop_column("category_groups", "icon")
