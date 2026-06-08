"""add activity events audit journal

Revision ID: 20260608_0029
Revises: 20260504_0028
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260608_0029"
down_revision = "20260504_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=24), server_default="web", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_events_user_id"), "activity_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_activity_events_actor_user_id"), "activity_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_activity_events_entity_type"), "activity_events", ["entity_type"], unique=False)
    op.create_index(op.f("ix_activity_events_entity_id"), "activity_events", ["entity_id"], unique=False)
    op.create_index(op.f("ix_activity_events_event_type"), "activity_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_activity_events_source"), "activity_events", ["source"], unique=False)
    op.create_index(op.f("ix_activity_events_created_at"), "activity_events", ["created_at"], unique=False)
    op.create_index("ix_activity_events_entity", "activity_events", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_activity_events_user_entity", "activity_events", ["user_id", "entity_type", "entity_id"], unique=False)

    for table_name, entity_type, title in (
        ("operations", "operation", "Операция уже существовала"),
        ("debts", "debt", "Долг уже существовал"),
        ("plan_operations", "plan", "План уже существовал"),
        ("categories", "category", "Категория уже существовала"),
        ("category_groups", "category_group", "Группа категорий уже существовала"),
        ("operation_item_templates", "item_template", "Позиция каталога уже существовала"),
        ("fx_trades", "currency_trade", "Валютная сделка уже существовала"),
    ):
        op.execute(
            sa.text(
                f"""
                INSERT INTO activity_events (
                    user_id, actor_user_id, entity_type, entity_id, event_type, title, changes, metadata, source, created_at
                )
                SELECT
                    user_id,
                    NULL,
                    :entity_type,
                    id,
                    'existing',
                    :title,
                    '[]',
                    '{{}}',
                    'migration',
                    COALESCE(created_at, CURRENT_TIMESTAMP)
                FROM {table_name}
                WHERE user_id IS NOT NULL
                """
            ).bindparams(entity_type=entity_type, title=title)
        )


def downgrade() -> None:
    op.drop_index("ix_activity_events_user_entity", table_name="activity_events")
    op.drop_index("ix_activity_events_entity", table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_created_at"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_source"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_event_type"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_entity_id"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_entity_type"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_actor_user_id"), table_name="activity_events")
    op.drop_index(op.f("ix_activity_events_user_id"), table_name="activity_events")
    op.drop_table("activity_events")
