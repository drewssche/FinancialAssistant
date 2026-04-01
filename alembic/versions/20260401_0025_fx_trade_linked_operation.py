"""fx trade linked operation settlement

Revision ID: 20260401_0025
Revises: 20260328_0024
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_0025"
down_revision = "20260328_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fx_trades", sa.Column("trade_kind", sa.String(length=24), nullable=False, server_default="manual"))
    op.add_column("fx_trades", sa.Column("linked_operation_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_fx_trades_trade_kind"), "fx_trades", ["trade_kind"], unique=False)
    op.create_index(op.f("ix_fx_trades_linked_operation_id"), "fx_trades", ["linked_operation_id"], unique=False)
    op.create_foreign_key(
        "fk_fx_trades_linked_operation_id_operations",
        "fx_trades",
        "operations",
        ["linked_operation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("fx_trades", "trade_kind", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_fx_trades_linked_operation_id_operations", "fx_trades", type_="foreignkey")
    op.drop_index(op.f("ix_fx_trades_linked_operation_id"), table_name="fx_trades")
    op.drop_index(op.f("ix_fx_trades_trade_kind"), table_name="fx_trades")
    op.drop_column("fx_trades", "linked_operation_id")
    op.drop_column("fx_trades", "trade_kind")
