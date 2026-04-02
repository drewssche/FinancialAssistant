"""backfill linked card payment trades

Revision ID: 20260402_0026
Revises: 20260401_0025
Create Date: 2026-04-02
"""

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "20260402_0026"
down_revision = "20260401_0025"
branch_labels = None
depends_on = None

MONEY_Q = Decimal("0.01")
MAX_CREATED_AT_DELTA_SECONDS = 600


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(MONEY_Q)


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    fx_trades = sa.Table(
        "fx_trades",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("side", sa.String(length=10)),
        sa.Column("quote_currency", sa.String(length=3)),
        sa.Column("quantity", sa.Numeric(18, 6)),
        sa.Column("unit_price", sa.Numeric(18, 6)),
        sa.Column("trade_kind", sa.String(length=24)),
        sa.Column("linked_operation_id", sa.Integer()),
        sa.Column("trade_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    operations = sa.Table(
        "operations",
        metadata,
        sa.Column("id", sa.Integer()),
        sa.Column("user_id", sa.Integer()),
        sa.Column("kind", sa.String(length=20)),
        sa.Column("amount", sa.Numeric(14, 2)),
        sa.Column("base_currency", sa.String(length=3)),
        sa.Column("operation_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    trade_rows = list(
        bind.execute(
            sa.select(
                fx_trades.c.id,
                fx_trades.c.user_id,
                fx_trades.c.quote_currency,
                fx_trades.c.quantity,
                fx_trades.c.unit_price,
                fx_trades.c.trade_date,
                fx_trades.c.created_at,
            )
            .where(
                fx_trades.c.trade_kind == "card_payment",
                fx_trades.c.linked_operation_id.is_(None),
                fx_trades.c.side == "sell",
            )
            .order_by(fx_trades.c.user_id.asc(), fx_trades.c.trade_date.asc(), fx_trades.c.id.asc())
        ).mappings()
    )
    if not trade_rows:
        return
    already_linked_operation_ids = {
        int(row[0])
        for row in bind.execute(
            sa.select(fx_trades.c.linked_operation_id).where(fx_trades.c.linked_operation_id.is_not(None))
        ).all()
        if row[0] is not None
    }
    for trade in trade_rows:
        quote_total = _money(Decimal(trade["quantity"] or 0) * Decimal(trade["unit_price"] or 0))
        candidate_rows = [
            row
            for row in bind.execute(
                sa.select(
                    operations.c.id,
                    operations.c.created_at,
                )
                .where(
                    operations.c.user_id == trade["user_id"],
                    operations.c.kind == "expense",
                    operations.c.operation_date == trade["trade_date"],
                    operations.c.amount == quote_total,
                    operations.c.base_currency == str(trade["quote_currency"] or "BYN").upper(),
                )
                .order_by(operations.c.created_at.asc(), operations.c.id.asc())
            ).mappings()
            if int(row["id"]) not in already_linked_operation_ids
        ]
        matched_operation_id = None
        if len(candidate_rows) == 1:
            matched_operation_id = int(candidate_rows[0]["id"])
        elif len(candidate_rows) > 1 and trade["created_at"] is not None:
            nearby_rows = []
            for row in candidate_rows:
                operation_created_at = row["created_at"]
                if operation_created_at is None:
                    continue
                delta_seconds = abs((operation_created_at - trade["created_at"]).total_seconds())
                if delta_seconds <= MAX_CREATED_AT_DELTA_SECONDS:
                    nearby_rows.append((delta_seconds, int(row["id"])))
            if len(nearby_rows) == 1:
                matched_operation_id = nearby_rows[0][1]
        if matched_operation_id is None:
            continue
        bind.execute(
            fx_trades.update()
            .where(fx_trades.c.id == int(trade["id"]))
            .values(linked_operation_id=matched_operation_id)
        )
        already_linked_operation_ids.add(matched_operation_id)


def downgrade() -> None:
    # Data backfill is intentionally irreversible.
    pass
