"""add operation and plan FX rate policies

Revision ID: 20260819_0038
Revises: 20260819_0037
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_0038"
down_revision = "20260819_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("operations", sa.Column("fx_rate_source", sa.String(length=16), nullable=True))
    op.add_column("operations", sa.Column("fx_bank_code", sa.String(length=32), nullable=True))
    op.add_column("operations", sa.Column("fx_bank_name", sa.String(length=100), nullable=True))
    op.add_column("operations", sa.Column("fx_bank_channel", sa.String(length=20), nullable=True))
    op.add_column("operations", sa.Column("fx_rate_kind", sa.String(length=8), nullable=True))
    op.add_column(
        "operations",
        sa.Column("fx_rate_scale", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("operations", sa.Column("fx_rate_date", sa.Date(), nullable=True))
    op.add_column("operations", sa.Column("fx_quoted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("operations", sa.Column("fx_fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "operations",
        sa.Column("fx_rate_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "operations",
        sa.Column("fx_payment_mode", sa.String(length=24), server_default="valuation", nullable=False),
    )
    op.create_check_constraint(
        "ck_operations_fx_rate_source",
        "operations",
        "fx_rate_source IS NULL OR fx_rate_source IN ('nbrb', 'bank', 'manual')",
    )
    op.create_check_constraint(
        "ck_operations_fx_rate_kind",
        "operations",
        "fx_rate_kind IS NULL OR fx_rate_kind IN ('buy', 'sell')",
    )
    op.create_check_constraint(
        "ck_operations_fx_payment_mode",
        "operations",
        "fx_payment_mode IN ('valuation', 'direct_conversion', 'foreign_balance')",
    )
    op.execute(sa.text("UPDATE operations SET fx_rate_scale = 100 WHERE UPPER(currency) = 'RUB'"))
    op.execute(
        sa.text(
            """
            UPDATE operations o
               SET fx_payment_mode = 'foreign_balance'
             WHERE EXISTS (
                 SELECT 1 FROM fx_trades t WHERE t.linked_operation_id = o.id
             )
               AND UPPER(o.currency) <> UPPER(o.base_currency)
            """
        )
    )

    op.add_column(
        "plan_operations",
        sa.Column("fx_rate_source", sa.String(length=16), server_default="nbrb", nullable=False),
    )
    op.add_column("plan_operations", sa.Column("fx_bank_code", sa.String(length=32), nullable=True))
    op.add_column("plan_operations", sa.Column("fx_bank_channel", sa.String(length=20), nullable=True))
    op.add_column("plan_operations", sa.Column("fx_rate_kind", sa.String(length=8), nullable=True))
    op.add_column("plan_operations", sa.Column("fx_manual_rate", sa.Numeric(precision=18, scale=6), nullable=True))
    op.add_column(
        "plan_operations",
        sa.Column("fx_payment_mode", sa.String(length=24), server_default="valuation", nullable=False),
    )
    op.create_check_constraint(
        "ck_plan_operations_fx_rate_source",
        "plan_operations",
        "fx_rate_source IN ('nbrb', 'bank', 'manual')",
    )
    op.create_check_constraint(
        "ck_plan_operations_fx_rate_kind",
        "plan_operations",
        "fx_rate_kind IS NULL OR fx_rate_kind IN ('buy', 'sell')",
    )
    op.create_check_constraint(
        "ck_plan_operations_fx_payment_mode",
        "plan_operations",
        "fx_payment_mode IN ('valuation', 'direct_conversion', 'foreign_balance')",
    )

    event_columns = [
        sa.Column("original_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=True),
        sa.Column("fx_rate", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("fx_rate_source", sa.String(length=16), nullable=True),
        sa.Column("fx_bank_code", sa.String(length=32), nullable=True),
        sa.Column("fx_bank_name", sa.String(length=100), nullable=True),
        sa.Column("fx_bank_channel", sa.String(length=20), nullable=True),
        sa.Column("fx_rate_kind", sa.String(length=8), nullable=True),
        sa.Column("fx_rate_scale", sa.Integer(), nullable=True),
        sa.Column("fx_rate_date", sa.Date(), nullable=True),
        sa.Column("fx_quoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fx_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fx_rate_stale", sa.Boolean(), nullable=True),
        sa.Column("fx_payment_mode", sa.String(length=24), nullable=True),
    ]
    for column in event_columns:
        op.add_column("plan_operation_events", column)

    # Before policy snapshots existed, a confirmed foreign-currency event kept
    # the plan's original amount in ``amount``.  Its linked operation is the
    # authoritative immutable conversion snapshot, so restore both the base
    # amount and provenance from it.  Skipped/reminded legacy rows have no
    # operation snapshot and deliberately remain nullable rather than being
    # guessed from a plan that may since have been edited.
    op.execute(
        sa.text(
            """
            UPDATE plan_operation_events AS event
               SET amount = operation.amount,
                   original_amount = operation.original_amount,
                   currency = operation.currency,
                   base_currency = operation.base_currency,
                   fx_rate = operation.fx_rate,
                   fx_rate_source = operation.fx_rate_source,
                   fx_bank_code = operation.fx_bank_code,
                   fx_bank_name = operation.fx_bank_name,
                   fx_bank_channel = operation.fx_bank_channel,
                   fx_rate_kind = operation.fx_rate_kind,
                   fx_rate_scale = operation.fx_rate_scale,
                   fx_rate_date = operation.fx_rate_date,
                   fx_quoted_at = operation.fx_quoted_at,
                   fx_fetched_at = operation.fx_fetched_at,
                   fx_rate_stale = operation.fx_rate_stale,
                   fx_payment_mode = operation.fx_payment_mode
              FROM operations AS operation
             WHERE event.operation_id = operation.id
               AND event.event_type = 'confirmed'
            """
        )
    )


def downgrade() -> None:
    for name in (
        "fx_payment_mode",
        "fx_rate_stale",
        "fx_fetched_at",
        "fx_quoted_at",
        "fx_rate_date",
        "fx_rate_scale",
        "fx_rate_kind",
        "fx_bank_channel",
        "fx_bank_name",
        "fx_bank_code",
        "fx_rate_source",
        "fx_rate",
        "base_currency",
        "currency",
        "original_amount",
    ):
        op.drop_column("plan_operation_events", name)

    op.drop_constraint("ck_plan_operations_fx_payment_mode", "plan_operations", type_="check")
    op.drop_constraint("ck_plan_operations_fx_rate_kind", "plan_operations", type_="check")
    op.drop_constraint("ck_plan_operations_fx_rate_source", "plan_operations", type_="check")
    for name in (
        "fx_payment_mode",
        "fx_manual_rate",
        "fx_rate_kind",
        "fx_bank_channel",
        "fx_bank_code",
        "fx_rate_source",
    ):
        op.drop_column("plan_operations", name)

    op.drop_constraint("ck_operations_fx_payment_mode", "operations", type_="check")
    op.drop_constraint("ck_operations_fx_rate_kind", "operations", type_="check")
    op.drop_constraint("ck_operations_fx_rate_source", "operations", type_="check")
    for name in (
        "fx_payment_mode",
        "fx_rate_stale",
        "fx_fetched_at",
        "fx_quoted_at",
        "fx_rate_date",
        "fx_rate_scale",
        "fx_rate_kind",
        "fx_bank_channel",
        "fx_bank_name",
        "fx_bank_code",
        "fx_rate_source",
    ):
        op.drop_column("operations", name)
