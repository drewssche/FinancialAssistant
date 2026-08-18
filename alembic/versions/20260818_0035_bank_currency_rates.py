"""add current bank currency rates

Revision ID: 20260818_0035
Revises: 20260809_0034
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260818_0035"
down_revision = "20260809_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_bank_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="BYN"),
        sa.Column("scale", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("buy_rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("sell_rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="cash"),
        sa.Column("location_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bank_code",
            "currency",
            "base_currency",
            "channel",
            name="uq_fx_bank_rate_bank_currency_channel",
        ),
    )
    op.create_index(op.f("ix_fx_bank_rates_bank_code"), "fx_bank_rates", ["bank_code"], unique=False)
    op.create_index(op.f("ix_fx_bank_rates_currency"), "fx_bank_rates", ["currency"], unique=False)
    op.create_index(op.f("ix_fx_bank_rates_fetched_at"), "fx_bank_rates", ["fetched_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fx_bank_rates_fetched_at"), table_name="fx_bank_rates")
    op.drop_index(op.f("ix_fx_bank_rates_currency"), table_name="fx_bank_rates")
    op.drop_index(op.f("ix_fx_bank_rates_bank_code"), table_name="fx_bank_rates")
    op.drop_table("fx_bank_rates")

