from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import Debt, DebtCounterparty, DebtIssuance, DebtRepayment


class DebtRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_counterparty_by_name_ci(self, user_id: int, name_ci: str) -> DebtCounterparty | None:
        stmt = select(DebtCounterparty).where(
            DebtCounterparty.user_id == user_id,
            DebtCounterparty.name_ci == name_ci,
        )
        return self.db.scalar(stmt)

    def create_counterparty(self, user_id: int, name: str, name_ci: str) -> DebtCounterparty:
        item = DebtCounterparty(user_id=user_id, name=name, name_ci=name_ci)
        self.db.add(item)
        self.db.flush()
        return item

    def list_counterparties(self, user_id: int) -> list[DebtCounterparty]:
        stmt = select(DebtCounterparty).where(DebtCounterparty.user_id == user_id).order_by(DebtCounterparty.name)
        return list(self.db.scalars(stmt))

    def create_debt(
        self,
        user_id: int,
        counterparty_id: int,
        direction: str,
        principal: Decimal,
        start_date: date,
        due_date: date | None,
        note: str | None,
    ) -> Debt:
        item = Debt(
            user_id=user_id,
            counterparty_id=counterparty_id,
            direction=direction,
            principal=principal,
            start_date=start_date,
            due_date=due_date,
            note=note,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_debt_by_id_for_user(self, user_id: int, debt_id: int) -> Debt | None:
        stmt = select(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)
        return self.db.scalar(stmt)

    def list_debts_for_counterparties(self, user_id: int, counterparty_ids: list[int]) -> list[Debt]:
        if not counterparty_ids:
            return []
        stmt = (
            select(Debt)
            .where(Debt.user_id == user_id, Debt.counterparty_id.in_(counterparty_ids))
            .order_by(Debt.start_date.desc(), Debt.id.desc())
        )
        return list(self.db.scalars(stmt))

    def create_repayment(self, debt_id: int, amount: Decimal, repayment_date: date, note: str | None) -> DebtRepayment:
        item = DebtRepayment(debt_id=debt_id, amount=amount, repayment_date=repayment_date, note=note)
        self.db.add(item)
        self.db.flush()
        return item

    def create_issuance(self, debt_id: int, amount: Decimal, issuance_date: date, note: str | None) -> DebtIssuance:
        item = DebtIssuance(debt_id=debt_id, amount=amount, issuance_date=issuance_date, note=note)
        self.db.add(item)
        self.db.flush()
        return item

    def find_active_merge_candidate(self, user_id: int, counterparty_id: int, direction: str) -> Debt | None:
        repaid_subq = (
            select(
                DebtRepayment.debt_id.label("debt_id"),
                func.coalesce(func.sum(DebtRepayment.amount), 0).label("repaid_total"),
            )
            .group_by(DebtRepayment.debt_id)
            .subquery()
        )
        stmt = (
            select(Debt)
            .outerjoin(repaid_subq, Debt.id == repaid_subq.c.debt_id)
            .where(
                Debt.user_id == user_id,
                Debt.counterparty_id == counterparty_id,
                Debt.direction == direction,
                (Debt.principal - func.coalesce(repaid_subq.c.repaid_total, 0)) > 0,
            )
            .order_by(Debt.start_date.asc(), Debt.id.asc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def update_debt(self, debt: Debt, updates: dict) -> Debt:
        for key, value in updates.items():
            setattr(debt, key, value)
        self.db.flush()
        return debt

    def delete_debt(self, debt: Debt) -> None:
        self.db.delete(debt)
        self.db.flush()

    def list_repayments_for_debts(self, debt_ids: list[int]) -> list[DebtRepayment]:
        if not debt_ids:
            return []
        stmt = (
            select(DebtRepayment)
            .where(DebtRepayment.debt_id.in_(debt_ids))
            .order_by(DebtRepayment.repayment_date.desc(), DebtRepayment.id.desc())
        )
        return list(self.db.scalars(stmt))

    def list_issuances_for_debts(self, debt_ids: list[int]) -> list[DebtIssuance]:
        if not debt_ids:
            return []
        stmt = (
            select(DebtIssuance)
            .where(DebtIssuance.debt_id.in_(debt_ids))
            .order_by(DebtIssuance.issuance_date.desc(), DebtIssuance.id.desc())
        )
        return list(self.db.scalars(stmt))

    def repayment_total_for_debt(self, debt_id: int) -> Decimal:
        stmt = select(func.coalesce(func.sum(DebtRepayment.amount), 0)).where(DebtRepayment.debt_id == debt_id)
        total = self.db.scalar(stmt)
        return Decimal(total or 0)

    def list_active_dashboard_preview_rows(self, *, user_id: int) -> list:
        repaid_subq = (
            select(
                DebtRepayment.debt_id.label("debt_id"),
                func.coalesce(func.sum(DebtRepayment.amount), 0).label("repaid_total"),
            )
            .group_by(DebtRepayment.debt_id)
            .subquery()
        )
        outstanding_expr = Debt.principal - func.coalesce(repaid_subq.c.repaid_total, 0)
        stmt = (
            select(
                Debt.id,
                Debt.counterparty_id,
                DebtCounterparty.name,
                Debt.direction,
                Debt.principal,
                func.coalesce(repaid_subq.c.repaid_total, 0),
                outstanding_expr,
                Debt.start_date,
                Debt.due_date,
                Debt.note,
                Debt.created_at,
            )
            .join(DebtCounterparty, DebtCounterparty.id == Debt.counterparty_id)
            .outerjoin(repaid_subq, Debt.id == repaid_subq.c.debt_id)
            .where(
                Debt.user_id == user_id,
                outstanding_expr > 0,
            )
            .order_by(DebtCounterparty.name.asc(), Debt.start_date.desc(), Debt.id.desc())
        )
        return list(self.db.execute(stmt).all())

    def summary_active_totals(self, *, user_id: int) -> tuple[Decimal, Decimal, int]:
        repaid_subq = (
            select(
                DebtRepayment.debt_id.label("debt_id"),
                func.coalesce(func.sum(DebtRepayment.amount), 0).label("repaid_total"),
            )
            .group_by(DebtRepayment.debt_id)
            .subquery()
        )
        outstanding_expr = Debt.principal - func.coalesce(repaid_subq.c.repaid_total, 0)
        stmt = (
            select(
                func.coalesce(func.sum(case((Debt.direction == "lend", outstanding_expr), else_=0)), 0),
                func.coalesce(func.sum(case((Debt.direction == "borrow", outstanding_expr), else_=0)), 0),
                func.count(
                    func.distinct(
                        case(
                            (outstanding_expr > 0, Debt.counterparty_id),
                            else_=None,
                        )
                    )
                ),
            )
            .select_from(Debt)
            .outerjoin(repaid_subq, Debt.id == repaid_subq.c.debt_id)
            .where(
                Debt.user_id == user_id,
                outstanding_expr > 0,
            )
        )
        lend_total, borrow_total, active_cards = self.db.execute(stmt).one()
        return (
            Decimal(lend_total or 0),
            Decimal(borrow_total or 0),
            int(active_cards or 0),
        )
