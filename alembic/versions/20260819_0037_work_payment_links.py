"""add durable work payment links

Revision ID: 20260819_0037
Revises: 20260819_0036
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_0037"
down_revision = "20260819_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_payment_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("operation_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_operation_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("snapshot_operation_date", sa.Date(), nullable=False),
        sa.Column("snapshot_original_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("snapshot_currency", sa.String(length=3), nullable=False),
        sa.Column("snapshot_base_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("snapshot_base_currency", sa.String(length=3), nullable=False),
        sa.Column("snapshot_note", sa.Text(), nullable=True),
        sa.Column("snapshot_category_name", sa.String(length=120), nullable=True),
        sa.Column("forecast_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("forecast_currency", sa.String(length=3), nullable=True),
        sa.Column("forecast_base_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("forecast_base_currency", sa.String(length=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('salary', 'advance')", name="ck_work_payment_links_role"),
        sa.CheckConstraint(
            "source IN ('plan_confirmation', 'manual')",
            name="ck_work_payment_links_source",
        ),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "operation_id", name="uq_work_payment_links_user_operation"),
        sa.UniqueConstraint(
            "user_id",
            "snapshot_operation_id",
            name="uq_work_payment_links_user_snapshot_operation",
        ),
    )
    op.create_index(op.f("ix_work_payment_links_created_at"), "work_payment_links", ["created_at"])
    op.create_index(op.f("ix_work_payment_links_operation_id"), "work_payment_links", ["operation_id"])
    op.create_index(op.f("ix_work_payment_links_plan_id"), "work_payment_links", ["plan_id"])
    op.create_index(op.f("ix_work_payment_links_role"), "work_payment_links", ["role"])
    op.create_index(op.f("ix_work_payment_links_snapshot_operation_id"), "work_payment_links", ["snapshot_operation_id"])
    op.create_index(op.f("ix_work_payment_links_snapshot_operation_date"), "work_payment_links", ["snapshot_operation_date"])
    op.create_index(op.f("ix_work_payment_links_source"), "work_payment_links", ["source"])
    op.create_index(op.f("ix_work_payment_links_user_id"), "work_payment_links", ["user_id"])

    # Only plans currently selected in a work profile can be classified
    # unambiguously during migration. From this point on links are independent
    # from both profiles and plans.
    op.execute(
        sa.text(
            """
            WITH payroll_events AS (
                SELECT
                    e.*,
                    CASE
                        WHEN wp.salary_plan_id = e.plan_id THEN 'salary'
                        ELSE 'advance'
                    END AS payment_role,
                    ROW_NUMBER() OVER (
                        PARTITION BY e.user_id, COALESCE(e.operation_id, -e.id)
                        ORDER BY e.created_at ASC, e.id ASC
                    ) AS duplicate_rank
                FROM plan_operation_events e
                JOIN work_profiles wp
                  ON wp.user_id = e.user_id
                 AND (wp.salary_plan_id = e.plan_id OR wp.advance_plan_id = e.plan_id)
                WHERE e.event_type = 'confirmed'
                  AND e.kind = 'income'
            )
            INSERT INTO work_payment_links (
                user_id,
                operation_id,
                snapshot_operation_id,
                role,
                source,
                plan_id,
                snapshot_operation_date,
                snapshot_original_amount,
                snapshot_currency,
                snapshot_base_amount,
                snapshot_base_currency,
                snapshot_note,
                snapshot_category_name,
                forecast_amount,
                forecast_currency,
                forecast_base_amount,
                forecast_base_currency,
                created_at,
                updated_at
            )
            SELECT
                e.user_id,
                o.id,
                e.operation_id,
                e.payment_role,
                'plan_confirmation',
                e.plan_id,
                COALESCE(o.operation_date, e.effective_date),
                COALESCE(NULLIF(o.original_amount, 0), o.amount, e.amount),
                UPPER(
                    CASE
                        WHEN o.id IS NOT NULL THEN COALESCE(o.currency, o.base_currency, 'BYN')
                        ELSE COALESCE(p.base_currency, 'BYN')
                    END
                ),
                COALESCE(o.amount, e.amount),
                UPPER(COALESCE(o.base_currency, p.base_currency, o.currency, p.currency, 'BYN')),
                COALESCE(o.note, e.note),
                COALESCE(c.name, e.category_name),
                CASE
                    WHEN o.amount = e.amount AND NULLIF(o.original_amount, 0) IS NOT NULL
                        THEN o.original_amount
                    ELSE e.amount
                END,
                UPPER(
                    CASE
                        WHEN o.amount = e.amount AND NULLIF(o.original_amount, 0) IS NOT NULL
                            THEN COALESCE(o.currency, o.base_currency, 'BYN')
                        ELSE COALESCE(o.base_currency, p.base_currency, 'BYN')
                    END
                ),
                e.amount,
                UPPER(COALESCE(o.base_currency, p.base_currency, 'BYN')),
                e.created_at,
                e.created_at
            FROM payroll_events e
            LEFT JOIN operations o
              ON o.id = e.operation_id
             AND o.user_id = e.user_id
             AND o.kind = 'income'
            LEFT JOIN categories c ON c.id = o.category_id
            LEFT JOIN plan_operations p
              ON p.id = e.plan_id
             AND p.user_id = e.user_id
            WHERE e.duplicate_rank = 1
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_work_payment_links_user_id"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_source"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_snapshot_operation_date"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_snapshot_operation_id"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_role"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_plan_id"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_operation_id"), table_name="work_payment_links")
    op.drop_index(op.f("ix_work_payment_links_created_at"), table_name="work_payment_links")
    op.drop_table("work_payment_links")
