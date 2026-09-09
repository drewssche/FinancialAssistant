from datetime import date
from decimal import Decimal

from app.repositories.work_earnings_repo import WorkEarningsRepository
from app.repositories.work_repo import WorkRepository


class WorkEarningsService:
    """Actual earnings by payment date, using stored currency conversion snapshots.

    Payroll categories follow the salary-cycle contract: current linked plans
    and previously confirmed payroll plans. A manual payment link counts only
    its own operation, without promoting unrelated income from its category.
    """

    def __init__(self, db, *, user_id: int):
        self.user_id = user_id
        self.repo = WorkEarningsRepository(db)
        work = WorkRepository(db)
        self.category_ids = work.list_known_payroll_category_ids(user_id=user_id)
        profile = work.get_profile(user_id=user_id)
        if profile:
            for plan_id in (profile.advance_plan_id, profile.salary_plan_id):
                plan = work.get_plan(user_id=user_id, plan_id=plan_id) if plan_id else None
                if plan and plan.kind == "income" and plan.category_id is not None:
                    self.category_ids.add(int(plan.category_id))

    def first_payment_date(self, *, today: date):
        return self.repo.first_payment_date(
            user_id=self.user_id, category_ids=self.category_ids, received_through=today,
        )

    def summarize(self, *, date_from: date, date_to: date, today: date) -> tuple[dict, dict]:
        totals: dict[str, Decimal] = {}
        months: dict[str, list[dict]] = {}
        operation_count = 0
        for row in self.repo.monthly_totals(
            user_id=self.user_id, category_ids=self.category_ids,
            date_from=date_from, date_to=date_to, received_through=today,
        ):
            amount = Decimal(row.amount).quantize(Decimal("0.01"))
            currency = row.currency
            totals[currency] = totals.get(currency, Decimal("0.00")) + amount
            operation_count += row.operation_count
            months.setdefault(f"{int(row.year):04d}-{int(row.month):02d}", []).append(
                {"currency": currency, "amount": amount},
            )
        return {
            "totals": [{"currency": currency, "amount": amount} for currency, amount in sorted(totals.items())],
            "operation_count": operation_count,
            "received_through": min(today, date_to),
        }, months
