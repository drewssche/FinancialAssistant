"""add category groups and hierarchy

Revision ID: 20260303_0004
Revises: 20260302_0003
Create Date: 2026-03-03 10:40:00

"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_0004"
down_revision = "20260302_0003"
branch_labels = None
depends_on = None

GROUP_SEED = {
    "income": [
        ("Основной доход", "#3ddc97", ["ЗП", "Дополнительный"]),
        ("Прочие поступления", "#6ec8ff", ["Возврат", "Скидка/кешбек", "Подарок+", "Находка"]),
    ],
    "expense": [
        ("Базовые платежи", "#5aa6ff", ["Коммуналка", "Телефон", "Интернет", "Налоги/Комиссии", "Штрафы"]),
        ("Еда", "#4fb9a7", ["Продукты и быт", "Обед на работе", "Кофе", "Снеки и сладости"]),
        ("Здоровье и уход", "#6ca5ff", ["Здоровье", "Гигиена/Бытовая химия", "Барбер", "Сигареты"]),
        (
            "Покупки и сервис",
            "#7b98ff",
            ["Онлайн-покупки", "Одежда", "Техника и инструменты", "Ремонт/сервисный центр"],
        ),
        ("Досуг", "#8f8cff", ["Игры/Софт/Курсы", "Отдых/Путешествие", "Заведения", "Тренировки", "Проезд"]),
        (
            "Подарки и форс-мажоры",
            "#c188ff",
            ["Дни рождения/Подарки", "Подарок-", "Потеря/Украдено", "Подписки"],
        ),
    ],
}


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "category_groups" not in existing_tables:
        op.create_table(
            "category_groups",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("kind", sa.String(length=16), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("color", sa.String(length=16), nullable=False, server_default="#7aa7ff"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("kind", "name", name="uq_category_group_kind_name"),
        )
        op.create_index(op.f("ix_category_groups_kind"), "category_groups", ["kind"], unique=False)
        op.create_index(op.f("ix_category_groups_name"), "category_groups", ["name"], unique=False)

    category_columns = {col["name"] for col in inspector.get_columns("categories")}
    if "group_id" not in category_columns:
        op.add_column("categories", sa.Column("group_id", sa.Uuid(), nullable=True))
    if "sort_order" not in category_columns:
        op.add_column("categories", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    if "is_archived" not in category_columns:
        op.add_column("categories", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))

    category_indexes = {idx["name"] for idx in inspector.get_indexes("categories")}
    if op.f("ix_categories_group_id") not in category_indexes:
        op.create_index(op.f("ix_categories_group_id"), "categories", ["group_id"], unique=False)

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("categories")}
    if "fk_categories_group_id_category_groups" not in fk_names:
        op.create_foreign_key(
            "fk_categories_group_id_category_groups",
            "categories",
            "category_groups",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )

    now = datetime.now(timezone.utc)

    for kind, groups in GROUP_SEED.items():
        for group_idx, (group_name, group_color, categories) in enumerate(groups):
            group_id = conn.execute(
                sa.text(
                    "SELECT id FROM category_groups WHERE kind=:kind AND name=:name"
                ),
                {"kind": kind, "name": group_name},
            ).scalar()
            if group_id is None:
                group_id = uuid4()
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO category_groups
                            (id, kind, name, color, sort_order, is_system, is_archived, created_at, updated_at)
                        VALUES
                            (:id, :kind, :name, :color, :sort_order, true, false, :created_at, :updated_at)
                        """
                    ),
                    {
                        "id": group_id,
                        "kind": kind,
                        "name": group_name,
                        "color": group_color,
                        "sort_order": group_idx,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
            else:
                conn.execute(
                    sa.text(
                        """
                        UPDATE category_groups
                        SET color=:color, sort_order=:sort_order, is_archived=false
                        WHERE id=:id
                        """
                    ),
                    {"id": group_id, "color": group_color, "sort_order": group_idx},
                )
            for category_idx, category_name in enumerate(categories):
                conn.execute(
                    sa.text(
                        """
                        UPDATE categories
                        SET group_id=:group_id, sort_order=:sort_order, is_archived=false
                        WHERE kind=:kind AND name=:name
                        """
                    ),
                    {
                        "group_id": group_id,
                        "sort_order": category_idx,
                        "kind": kind,
                        "name": category_name,
                    },
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("categories")}
    if "fk_categories_group_id_category_groups" in fk_names:
        op.drop_constraint("fk_categories_group_id_category_groups", "categories", type_="foreignkey")

    category_indexes = {idx["name"] for idx in inspector.get_indexes("categories")}
    if op.f("ix_categories_group_id") in category_indexes:
        op.drop_index(op.f("ix_categories_group_id"), table_name="categories")

    category_columns = {col["name"] for col in inspector.get_columns("categories")}
    if "is_archived" in category_columns:
        op.drop_column("categories", "is_archived")
    if "sort_order" in category_columns:
        op.drop_column("categories", "sort_order")
    if "group_id" in category_columns:
        op.drop_column("categories", "group_id")

    if "category_groups" in inspector.get_table_names():
        group_indexes = {idx["name"] for idx in inspector.get_indexes("category_groups")}
        if op.f("ix_category_groups_name") in group_indexes:
            op.drop_index(op.f("ix_category_groups_name"), table_name="category_groups")
        if op.f("ix_category_groups_kind") in group_indexes:
            op.drop_index(op.f("ix_category_groups_kind"), table_name="category_groups")
        op.drop_table("category_groups")
