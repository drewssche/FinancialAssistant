"""add daily bank currency rate history

Revision ID: 20260826_0039
Revises: 20260819_0038
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0039"
down_revision = "20260819_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_bank_rate_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="BYN"),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("scale", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("buy_rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("sell_rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="cash"),
        sa.Column("location_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bank_code",
            "currency",
            "base_currency",
            "channel",
            "rate_date",
            name="uq_fx_bank_rate_snapshot_bank_currency_channel_date",
        ),
    )
    op.create_index(
        op.f("ix_fx_bank_rate_snapshots_bank_code"),
        "fx_bank_rate_snapshots",
        ["bank_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fx_bank_rate_snapshots_currency"),
        "fx_bank_rate_snapshots",
        ["currency"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fx_bank_rate_snapshots_fetched_at"),
        "fx_bank_rate_snapshots",
        ["fetched_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fx_bank_rate_snapshots_rate_date"),
        "fx_bank_rate_snapshots",
        ["rate_date"],
        unique=False,
    )

    # The legacy table contains only each provider's latest quote.  Preserve
    # exactly that observation as a single starting point; older values cannot
    # be reconstructed honestly from the available data.
    op.execute(
        sa.text(
            """
            INSERT INTO fx_bank_rate_snapshots (
                bank_code, bank_name, currency, base_currency, rate_date,
                scale, buy_rate, sell_rate, channel, location_name, source_url,
                quoted_at, fetched_at
            )
            SELECT bank_code,
                   bank_name,
                   currency,
                   base_currency,
                   CAST(COALESCE(quoted_at, fetched_at) AT TIME ZONE 'Europe/Minsk' AS DATE),
                   scale,
                   buy_rate,
                   sell_rate,
                   channel,
                   location_name,
                   source_url,
                   quoted_at,
                   fetched_at
              FROM fx_bank_rates
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_fx_bank_rate_snapshots_rate_date"), table_name="fx_bank_rate_snapshots")
    op.drop_index(op.f("ix_fx_bank_rate_snapshots_fetched_at"), table_name="fx_bank_rate_snapshots")
    op.drop_index(op.f("ix_fx_bank_rate_snapshots_currency"), table_name="fx_bank_rate_snapshots")
    op.drop_index(op.f("ix_fx_bank_rate_snapshots_bank_code"), table_name="fx_bank_rate_snapshots")
    op.drop_table("fx_bank_rate_snapshots")
