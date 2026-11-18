from datetime import date
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from app.db.base import Base
from app.db.models import ActivityEvent, FxTrade, Operation, OperationReceiptItem, User


def test_migration_preserves_receipt_and_manual_exchange_and_rejects_future_debits(monkeypatch):
    script = ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20261118_0059").module
    day = date(2026, 3, 6)
    with sa.create_engine("sqlite://").begin() as conn:
        Base.metadata.create_all(conn)
        monkeypatch.setattr(script, "op", Operations(MigrationContext.configure(conn)))
        script.downgrade()
        conn.execute(sa.insert(User).values(id=1, display_name="Test", status="active"))
        conn.execute(sa.insert(Operation).values(id=7, user_id=1, kind="expense", amount=12,
                     original_amount=12, currency="BYN", base_currency="BYN", fx_rate=1, operation_date=day))
        conn.execute(sa.insert(OperationReceiptItem).values(id=5, operation_id=7, user_id=1, name="Товар",
                     quantity=2, unit_price=6, regular_unit_price=7, is_discounted=True, line_total=12))
        trade = dict(user_id=1, asset_currency="USD", quote_currency="BYN", quantity=4, unit_price=3, trade_date=day)
        conn.execute(sa.insert(FxTrade).values(**trade, id=8, side="buy", trade_kind="manual"))
        debit = sa.insert(FxTrade).values(**trade, id=9, side="sell", trade_kind="card_payment", linked_operation_id=7)
        conn.execute(debit)
        receipt_before = conn.execute(sa.select(OperationReceiptItem)).one()
        manual = sa.select(FxTrade).where(FxTrade.id == 8)
        exchange_before = conn.execute(manual).one()

        script.upgrade()

        saved = conn.execute(sa.select(Operation)).mappings().one()
        assert (saved["amount"], saved["original_amount"], saved["currency"], saved["receipt_currency"]) == (12, 4, "USD", "BYN")
        assert (saved["fx_rate"], saved["fx_rate_date"], saved["fx_payment_mode"]) == (Decimal(3), day, "valuation")
        assert conn.execute(sa.select(OperationReceiptItem)).one() == receipt_before
        assert conn.execute(sa.select(FxTrade)).one() == exchange_before
        assert conn.scalar(sa.select(ActivityEvent.event_type)) == "payment_valuation"
        with pytest.raises(sa.exc.IntegrityError, match="ck_fx_trades_no_expense_debit"), conn.begin_nested():
            conn.execute(debit)
        with pytest.raises(RuntimeError, match="backup"):
            script.downgrade()
