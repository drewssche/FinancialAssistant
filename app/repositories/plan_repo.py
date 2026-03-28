from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, delete, desc, or_, select
from sqlalchemy.orm import Session, aliased

from app.db.models import (
    AuthIdentity,
    Category,
    CategoryGroup,
    PlanOperation,
    PlanOperationEvent,
    PlanReminderJob,
    PlanReceiptItem,
    UserPreference,
)


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def _base_stmt(self, *, user_id: int):
        group = aliased(CategoryGroup)
        return (
            select(PlanOperation, Category, group)
            .outerjoin(Category, Category.id == PlanOperation.category_id)
            .outerjoin(group, group.id == Category.group_id)
            .where(PlanOperation.user_id == user_id)
        )

    def create(
        self,
        *,
        user_id: int,
        kind: str,
        amount: Decimal,
        original_amount: Decimal,
        currency: str,
        base_currency: str,
        scheduled_date: date,
        category_id: int | None,
        note: str | None,
        recurrence_enabled: bool,
        recurrence_frequency: str | None,
        recurrence_interval: int,
        recurrence_weekdays: str | None,
        recurrence_workdays_only: bool,
        recurrence_month_end: bool,
        recurrence_end_date: date | None,
    ) -> PlanOperation:
        item = PlanOperation(
            user_id=user_id,
            kind=kind,
            amount=amount,
            original_amount=original_amount,
            currency=currency,
            base_currency=base_currency,
            scheduled_date=scheduled_date,
            category_id=category_id,
            note=note,
            recurrence_enabled=recurrence_enabled,
            recurrence_frequency=recurrence_frequency,
            recurrence_interval=recurrence_interval,
            recurrence_weekdays=recurrence_weekdays,
            recurrence_workdays_only=recurrence_workdays_only,
            recurrence_month_end=recurrence_month_end,
            recurrence_end_date=recurrence_end_date,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_by_id(self, *, user_id: int, plan_id: int):
        stmt = self._base_stmt(user_id=user_id).where(PlanOperation.id == plan_id)
        return self.db.execute(stmt).first()

    def list_for_user(self, *, user_id: int, q: str | None = None, kind: str | None = None):
        stmt = self._base_stmt(user_id=user_id)
        if kind:
            stmt = stmt.where(PlanOperation.kind == kind)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    PlanOperation.note.like(like),
                    Category.name.like(like),
                )
            )
        stmt = stmt.order_by(
            PlanOperation.status.asc(),
            PlanOperation.scheduled_date.asc(),
            desc(PlanOperation.id),
        )
        return list(self.db.execute(stmt).all())

    def update(self, item: PlanOperation, updates: dict) -> PlanOperation:
        for key, value in updates.items():
            setattr(item, key, value)
        return item

    def delete(self, item: PlanOperation) -> None:
        self.db.delete(item)

    def get_category_name(self, *, category_id: int | None) -> str | None:
        if not category_id:
            return None
        return self.db.scalar(select(Category.name).where(Category.id == category_id))

    def replace_receipt_items(self, *, user_id: int, plan_id: int, items: list[dict]) -> list[PlanReceiptItem]:
        self.db.execute(
            delete(PlanReceiptItem).where(
                and_(
                    PlanReceiptItem.user_id == user_id,
                    PlanReceiptItem.plan_id == plan_id,
                )
            )
        )
        created: list[PlanReceiptItem] = []
        for item in items:
            row = PlanReceiptItem(
                user_id=user_id,
                plan_id=plan_id,
                category_id=item.get("category_id"),
                shop_name=item.get("shop_name"),
                name=item["name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                line_total=item["line_total"],
                note=item.get("note"),
            )
            self.db.add(row)
            created.append(row)
        self.db.flush()
        return created

    def list_receipt_items_for_plans(self, *, user_id: int, plan_ids: list[int]) -> dict[int, list[PlanReceiptItem]]:
        if not plan_ids:
            return {}
        stmt = (
            select(PlanReceiptItem)
            .where(
                PlanReceiptItem.user_id == user_id,
                PlanReceiptItem.plan_id.in_(plan_ids),
            )
            .order_by(PlanReceiptItem.id.asc())
        )
        grouped: dict[int, list[PlanReceiptItem]] = {plan_id: [] for plan_id in plan_ids}
        for row in self.db.scalars(stmt):
            grouped.setdefault(int(row.plan_id), []).append(row)
        return grouped

    def list_next_pending_jobs_for_plans(self, *, user_id: int, plan_ids: list[int]) -> dict[int, PlanReminderJob]:
        if not plan_ids:
            return {}
        stmt = (
            select(PlanReminderJob)
            .where(
                PlanReminderJob.user_id == user_id,
                PlanReminderJob.plan_id.in_(plan_ids),
                PlanReminderJob.status == "pending",
            )
            .order_by(PlanReminderJob.plan_id.asc(), PlanReminderJob.scheduled_for.asc(), PlanReminderJob.id.asc())
        )
        grouped: dict[int, PlanReminderJob] = {}
        for row in self.db.scalars(stmt):
            grouped.setdefault(int(row.plan_id), row)
        return grouped

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

    def list_user_plan_reminder_targets(self) -> list:
        stmt = (
            select(AuthIdentity, UserPreference)
            .outerjoin(UserPreference, UserPreference.user_id == AuthIdentity.user_id)
            .where(AuthIdentity.provider == "telegram")
        )
        return list(self.db.execute(stmt).all())

    def list_due_reminder_jobs(self, *, now_utc: datetime) -> list:
        stmt = (
            select(PlanReminderJob, PlanOperation, AuthIdentity, UserPreference)
            .join(PlanOperation, PlanOperation.id == PlanReminderJob.plan_id)
            .outerjoin(
                AuthIdentity,
                and_(
                    AuthIdentity.user_id == PlanReminderJob.user_id,
                    AuthIdentity.provider == "telegram",
                ),
            )
            .outerjoin(UserPreference, UserPreference.user_id == PlanReminderJob.user_id)
            .where(
                PlanReminderJob.status == "pending",
                PlanReminderJob.scheduled_for <= now_utc,
            )
            .order_by(PlanReminderJob.scheduled_for.asc(), PlanReminderJob.id.asc())
        )
        return list(self.db.execute(stmt).all())

    def get_pending_reminder_job_snapshot(self, *, job_id: int):
        stmt = (
            select(PlanReminderJob, PlanOperation, AuthIdentity, UserPreference)
            .join(PlanOperation, PlanOperation.id == PlanReminderJob.plan_id)
            .outerjoin(
                AuthIdentity,
                and_(
                    AuthIdentity.user_id == PlanReminderJob.user_id,
                    AuthIdentity.provider == "telegram",
                ),
            )
            .outerjoin(UserPreference, UserPreference.user_id == PlanReminderJob.user_id)
            .where(
                PlanReminderJob.id == job_id,
                PlanReminderJob.status == "pending",
            )
            .limit(1)
        )
        return self.db.execute(stmt).first()

    def create_reminder_job(self, *, user_id: int, plan_id: int, scheduled_for: datetime) -> PlanReminderJob:
        row = PlanReminderJob(
            user_id=user_id,
            plan_id=plan_id,
            scheduled_for=scheduled_for,
            status="pending",
        )
        self.db.add(row)
        self.db.flush()
        return row

    def cancel_pending_reminder_jobs(self, *, user_id: int, plan_id: int, canceled_at: datetime) -> None:
        stmt = select(PlanReminderJob).where(
            PlanReminderJob.user_id == user_id,
            PlanReminderJob.plan_id == plan_id,
            PlanReminderJob.status == "pending",
        )
        for row in self.db.scalars(stmt):
            row.status = "canceled"
            row.canceled_at = canceled_at

    def mark_reminder_job_sent(self, job: PlanReminderJob, *, sent_at: datetime) -> None:
        job.status = "sent"
        job.sent_at = sent_at

    def create_event(
        self,
        *,
        user_id: int,
        plan_id: int,
        operation_id: int | None,
        event_type: str,
        kind: str,
        amount: Decimal,
        effective_date: date,
        note: str | None,
        category_name: str | None,
    ) -> PlanOperationEvent:
        row = PlanOperationEvent(
            user_id=user_id,
            plan_id=plan_id,
            operation_id=operation_id,
            event_type=event_type,
            kind=kind,
            amount=amount,
            effective_date=effective_date,
            note=note,
            category_name=category_name,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_history_for_user(self, *, user_id: int, q: str | None = None, kind: str | None = None) -> list[PlanOperationEvent]:
        stmt = select(PlanOperationEvent).where(PlanOperationEvent.user_id == user_id)
        if kind:
            stmt = stmt.where(PlanOperationEvent.kind == kind)
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    PlanOperationEvent.note.like(like),
                    PlanOperationEvent.category_name.like(like),
                )
            )
        stmt = stmt.order_by(PlanOperationEvent.created_at.desc(), PlanOperationEvent.id.desc())
        return list(self.db.scalars(stmt))

    def list_active_plans_for_user(self, *, user_id: int) -> list[PlanOperation]:
        stmt = (
            select(PlanOperation)
            .where(
                PlanOperation.user_id == user_id,
                PlanOperation.status == "active",
            )
            .order_by(PlanOperation.scheduled_date.asc(), PlanOperation.id.asc())
        )
        return list(self.db.scalars(stmt))
