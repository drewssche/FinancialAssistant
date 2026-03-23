from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import AuthIdentity, Debt, DebtCounterparty, DebtIssuance, DebtReminderJob, DebtRepayment, UserPreference


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

    def get_counterparty_by_id(self, user_id: int, counterparty_id: int) -> DebtCounterparty | None:
        stmt = select(DebtCounterparty).where(
            DebtCounterparty.id == counterparty_id,
            DebtCounterparty.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_counterparties(self, user_id: int) -> list[DebtCounterparty]:
        stmt = select(DebtCounterparty).where(DebtCounterparty.user_id == user_id).order_by(DebtCounterparty.name)
        return list(self.db.scalars(stmt))

    def list_active_due_dated_debts_for_user(self, *, user_id: int) -> list[Debt]:
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
            select(Debt)
            .outerjoin(repaid_subq, Debt.id == repaid_subq.c.debt_id)
            .where(
                Debt.user_id == user_id,
                Debt.due_date.is_not(None),
                outstanding_expr > 0,
            )
            .order_by(Debt.due_date.asc(), Debt.id.asc())
        )
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

    def get_user_preferences(self, *, user_id: int) -> UserPreference | None:
        return self.db.scalar(select(UserPreference).where(UserPreference.user_id == user_id))

    def get_telegram_identity(self, *, user_id: int) -> AuthIdentity | None:
        return self.db.scalar(
            select(AuthIdentity)
            .where(
                AuthIdentity.user_id == user_id,
                AuthIdentity.provider == "telegram",
            )
            .limit(1)
        )

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

    def create_reminder_job(
        self,
        *,
        user_id: int,
        debt_id: int,
        event_type: str,
        scheduled_for,
    ) -> DebtReminderJob:
        row = DebtReminderJob(
            user_id=user_id,
            debt_id=debt_id,
            event_type=event_type,
            scheduled_for=scheduled_for,
            status="pending",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def cancel_pending_reminder_jobs(
        self,
        *,
        user_id: int,
        debt_id: int,
        event_type: str,
        canceled_at,
    ) -> None:
        stmt = select(DebtReminderJob).where(
            DebtReminderJob.user_id == user_id,
            DebtReminderJob.debt_id == debt_id,
            DebtReminderJob.event_type == event_type,
            DebtReminderJob.status == "pending",
        )
        for row in self.db.scalars(stmt):
            row.status = "canceled"
            row.canceled_at = canceled_at

    def mark_reminder_job_sent(self, job: DebtReminderJob, *, sent_at) -> None:
        job.status = "sent"
        job.sent_at = sent_at

    def get_latest_sent_reminder_job(self, *, user_id: int, debt_id: int, event_type: str) -> DebtReminderJob | None:
        stmt = (
            select(DebtReminderJob)
            .where(
                DebtReminderJob.user_id == user_id,
                DebtReminderJob.debt_id == debt_id,
                DebtReminderJob.event_type == event_type,
                DebtReminderJob.status == "sent",
                DebtReminderJob.sent_at.is_not(None),
            )
            .order_by(DebtReminderJob.sent_at.desc(), DebtReminderJob.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

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

    def list_due_reminder_jobs(self, *, now_utc) -> list:
        stmt = (
            select(DebtReminderJob, Debt, DebtCounterparty, AuthIdentity, UserPreference)
            .join(Debt, Debt.id == DebtReminderJob.debt_id)
            .join(DebtCounterparty, DebtCounterparty.id == Debt.counterparty_id)
            .outerjoin(
                AuthIdentity,
                (AuthIdentity.user_id == DebtReminderJob.user_id) & (AuthIdentity.provider == "telegram"),
            )
            .outerjoin(UserPreference, UserPreference.user_id == DebtReminderJob.user_id)
            .where(
                DebtReminderJob.status == "pending",
                DebtReminderJob.scheduled_for <= now_utc,
            )
            .order_by(DebtReminderJob.scheduled_for.asc(), DebtReminderJob.id.asc())
        )
        return list(self.db.execute(stmt).all())

    def get_pending_reminder_job_snapshot(self, *, job_id: int):
        stmt = (
            select(DebtReminderJob, Debt, DebtCounterparty, AuthIdentity, UserPreference)
            .join(Debt, Debt.id == DebtReminderJob.debt_id)
            .join(DebtCounterparty, DebtCounterparty.id == Debt.counterparty_id)
            .outerjoin(
                AuthIdentity,
                (AuthIdentity.user_id == DebtReminderJob.user_id) & (AuthIdentity.provider == "telegram"),
            )
            .outerjoin(UserPreference, UserPreference.user_id == DebtReminderJob.user_id)
            .where(
                DebtReminderJob.id == job_id,
                DebtReminderJob.status == "pending",
            )
            .limit(1)
        )
        return self.db.execute(stmt).first()

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
