"""Keep the actual payment and dated equivalent separately from original receipt prices."""
from datetime import date
from decimal import Decimal

from alembic import op
import sqlalchemy as sa

from app.core.legacy_card_payment import payment_valuation

revision = "20261118_0059"
down_revision = "20261118_0058"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("operations", sa.Column("receipt_currency", sa.String(3), nullable=True))
    db = op.get_bind()
    if db.dialect.name == "postgresql":
        db.execute(sa.text("LOCK TABLE operations, fx_trades, plan_operations IN SHARE ROW EXCLUSIVE MODE"))
    events = sa.table("activity_events", sa.column("user_id", sa.Integer), sa.column("entity_type", sa.String),
        sa.column("entity_id", sa.Integer), sa.column("event_type", sa.String), sa.column("title", sa.String),
        sa.column("source", sa.String), sa.column("metadata", sa.JSON))
    operations = sa.table("operations", sa.column("id", sa.Integer), sa.column("currency", sa.String),
        sa.column("original_amount", sa.Numeric), sa.column("fx_rate", sa.Numeric),
        sa.column("receipt_currency", sa.String), sa.column("fx_rate_source", sa.String),
        sa.column("fx_bank_code", sa.String), sa.column("fx_bank_name", sa.String), sa.column("fx_bank_channel", sa.String),
        sa.column("fx_rate_kind", sa.String), sa.column("fx_quoted_at", sa.DateTime), sa.column("fx_fetched_at", sa.DateTime),
        sa.column("fx_rate_stale", sa.Boolean),
        sa.column("fx_rate_date", sa.Date), sa.column("fx_rate_scale", sa.Integer), sa.column("fx_payment_mode", sa.String))
    rows = db.execute(sa.text("""
        SELECT o.id, o.kind, o.currency, o.base_currency, o.amount, o.original_amount, o.fx_rate, o.fx_rate_date,
               f.id AS trade_id, f.asset_currency, f.quote_currency, f.side, f.trade_kind,
               f.quantity, f.unit_price, f.trade_date, f.fee, f.note AS charge_note, o.user_id AS owner, f.user_id AS trade_owner,
               EXISTS(SELECT 1 FROM operation_receipt_items r WHERE r.operation_id=o.id) AS has_receipt
          FROM fx_trades f JOIN operations o ON o.id=f.linked_operation_id ORDER BY o.id
    """)).mappings().all()
    seen = set()
    for row in rows:
        if (row["id"] in seen or row["owner"] != row["trade_owner"]
                or row["trade_kind"] != "card_payment" or Decimal(str(row["fee"])) != 0):
            raise ValueError(f"Review the linked currency trades for operation {row['id']}")
        seen.add(row["id"])
        values = payment_valuation(row, row, has_receipt=row["has_receipt"])
        if isinstance(values.get("fx_rate_date"), str):
            values["fx_rate_date"] = date.fromisoformat(values["fx_rate_date"])
        db.execute(operations.update().where(operations.c.id == row["id"]).values(**values))
        db.execute(events.insert().values(
            user_id=row["owner"], entity_type="operation", entity_id=row["id"], event_type="payment_valuation",
            source="system", title="Сохранена оплата в валюте по курсу на дату покупки",
            metadata={"amount": str(row["quantity"]), "currency": row["asset_currency"],
                      "equivalent": str(row["amount"]), "base_currency": row["base_currency"],
                      "rate": str(row["unit_price"]), "date": str(row["trade_date"]), "note": row["charge_note"]},
        ))
        db.execute(sa.text("DELETE FROM fx_trades WHERE id=:trade_id"), {"trade_id": row["trade_id"]})
    with op.batch_alter_table("fx_trades") as batch:
        batch.create_check_constraint("ck_fx_trades_no_expense_debit", "linked_operation_id IS NULL")
    for table in ("operations", "plan_operations"):
        db.execute(sa.text(f"UPDATE {table} SET fx_payment_mode='valuation' WHERE fx_payment_mode IN ('foreign_balance','direct_conversion')"))


def downgrade():
    # A downgrade would otherwise label base-currency receipt prices as foreign.
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM activity_events WHERE event_type='payment_valuation'")):
        raise RuntimeError("Restore the pre-migration database backup to downgrade converted receipts")
    with op.batch_alter_table("fx_trades") as batch:
        batch.drop_constraint("ck_fx_trades_no_expense_debit", type_="check")
    op.drop_column("operations", "receipt_currency")
