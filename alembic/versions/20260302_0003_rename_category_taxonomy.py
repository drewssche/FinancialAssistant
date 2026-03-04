"""rename category taxonomy

Revision ID: 20260302_0003
Revises: 20260302_0002
Create Date: 2026-03-02 21:05:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from datetime import datetime
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = "20260302_0003"
down_revision = "20260302_0002"
branch_labels = None
depends_on = None

RENAME_MAP = [
    ("expense", "Аптека/Мед услуги/БАДы", "Здоровье"),
    ("expense", "Продукты/Бытовые расходники", "Продукты и быт"),
    ("expense", "Кофейни/Кофе", "Кофе"),
    ("expense", "Снэки/Сладости", "Снеки и сладости"),
    ("expense", "Инет заказы", "Онлайн-покупки"),
    ("expense", "Техника/Инструменты/Разное", "Техника и инструменты"),
]


def _apply_rename(kind: str, old_name: str, new_name: str) -> None:
    conn = op.get_bind()

    old_id = conn.execute(
        sa.text("SELECT id FROM categories WHERE kind=:kind AND name=:name"),
        {"kind": kind, "name": old_name},
    ).scalar()
    new_id = conn.execute(
        sa.text("SELECT id FROM categories WHERE kind=:kind AND name=:name"),
        {"kind": kind, "name": new_name},
    ).scalar()

    conn.execute(
        sa.text(
            "UPDATE operations SET subcategory=:new_name "
            "WHERE kind=:kind AND subcategory=:old_name"
        ),
        {"kind": kind, "old_name": old_name, "new_name": new_name},
    )

    if old_id is not None and new_id is not None:
        conn.execute(sa.text("DELETE FROM categories WHERE id=:id"), {"id": old_id})
        return

    if old_id is not None and new_id is None:
        conn.execute(
            sa.text("UPDATE categories SET name=:new_name WHERE id=:id"),
            {"new_name": new_name, "id": old_id},
        )
        return

    if old_id is None and new_id is None:
        conn.execute(
            sa.text(
                "INSERT INTO categories (id, kind, name, is_system, created_at, updated_at) "
                "VALUES (:id, :kind, :name, true, :created_at, :updated_at)"
            ),
            {
                "id": uuid4(),
                "kind": kind,
                "name": new_name,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )


def upgrade() -> None:
    for kind, old_name, new_name in RENAME_MAP:
        _apply_rename(kind, old_name, new_name)


def downgrade() -> None:
    for kind, old_name, new_name in reversed(RENAME_MAP):
        _apply_rename(kind, new_name, old_name)
