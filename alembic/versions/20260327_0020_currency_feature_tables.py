"""add currency feature tables

Revision ID: 20260327_0020
Revises: 20260323_0019
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0020"
down_revision = "20260323_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("asset_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False, server_default="BYN"),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("fee", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fx_trades_user_id"), "fx_trades", ["user_id"], unique=False)
    op.create_index(op.f("ix_fx_trades_side"), "fx_trades", ["side"], unique=False)
    op.create_index(op.f("ix_fx_trades_asset_currency"), "fx_trades", ["asset_currency"], unique=False)
    op.create_index(op.f("ix_fx_trades_quote_currency"), "fx_trades", ["quote_currency"], unique=False)
    op.create_index(op.f("ix_fx_trades_trade_date"), "fx_trades", ["trade_date"], unique=False)

    op.create_table(
        "fx_rate_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "currency", "rate_date", name="uq_fx_rate_snapshot_user_currency_date"),
    )
    op.create_index(op.f("ix_fx_rate_snapshots_user_id"), "fx_rate_snapshots", ["user_id"], unique=False)
    op.create_index(op.f("ix_fx_rate_snapshots_currency"), "fx_rate_snapshots", ["currency"], unique=False)
    op.create_index(op.f("ix_fx_rate_snapshots_rate_date"), "fx_rate_snapshots", ["rate_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fx_rate_snapshots_rate_date"), table_name="fx_rate_snapshots")
    op.drop_index(op.f("ix_fx_rate_snapshots_currency"), table_name="fx_rate_snapshots")
    op.drop_index(op.f("ix_fx_rate_snapshots_user_id"), table_name="fx_rate_snapshots")
    op.drop_table("fx_rate_snapshots")

    op.drop_index(op.f("ix_fx_trades_trade_date"), table_name="fx_trades")
    op.drop_index(op.f("ix_fx_trades_quote_currency"), table_name="fx_trades")
    op.drop_index(op.f("ix_fx_trades_asset_currency"), table_name="fx_trades")
    op.drop_index(op.f("ix_fx_trades_side"), table_name="fx_trades")
    op.drop_index(op.f("ix_fx_trades_user_id"), table_name="fx_trades")
    op.drop_table("fx_trades")
