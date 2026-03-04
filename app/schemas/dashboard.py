from decimal import Decimal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
