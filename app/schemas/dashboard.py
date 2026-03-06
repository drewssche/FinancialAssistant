from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    debt_lend_outstanding: Decimal
    debt_borrow_outstanding: Decimal
    debt_net_position: Decimal
    active_debt_cards: int
