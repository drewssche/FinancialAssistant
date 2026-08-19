from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    Category,
    EmploymentContract,
    Operation,
    PlanOperation,
    PlanOperationEvent,
    WorkDayOverride,
    WorkProfile,
)


class WorkRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_profile(self, *, user_id: int) -> WorkProfile | None:
        return self.db.scalar(select(WorkProfile).where(WorkProfile.user_id == user_id))

    def create_profile(self, *, user_id: int) -> WorkProfile:
        profile = WorkProfile(user_id=user_id)
        self.db.add(profile)
        self.db.flush()
        return profile

    def get_plan(self, *, user_id: int, plan_id: int) -> PlanOperation | None:
        return self.db.scalar(
            select(PlanOperation).where(PlanOperation.user_id == user_id, PlanOperation.id == plan_id)
        )

    def list_confirmed_payroll_events(
        self,
        *,
        user_id: int,
        plan_ids: list[int],
        date_from: date,
        date_to: date,
    ) -> list:
        if not plan_ids:
            return []
        stmt = (
            select(PlanOperationEvent, Operation)
            .outerjoin(
                Operation,
                and_(
                    Operation.id == PlanOperationEvent.operation_id,
                    Operation.user_id == user_id,
                ),
            )
            .where(
                PlanOperationEvent.user_id == user_id,
                PlanOperationEvent.plan_id.in_(plan_ids),
                PlanOperationEvent.event_type == "confirmed",
                or_(
                    and_(
                        Operation.id.is_not(None),
                        Operation.operation_date >= date_from,
                        Operation.operation_date <= date_to,
                    ),
                    and_(
                        Operation.id.is_(None),
                        PlanOperationEvent.effective_date >= date_from,
                        PlanOperationEvent.effective_date <= date_to,
                    ),
                ),
            )
            .order_by(
                Operation.operation_date.desc(),
                PlanOperationEvent.effective_date.desc(),
                PlanOperationEvent.id.desc(),
            )
        )
        return list(self.db.execute(stmt).all())

    def list_overrides(self, *, user_id: int, date_from: date, date_to: date) -> list[WorkDayOverride]:
        return list(
            self.db.scalars(
                select(WorkDayOverride)
                .where(
                    WorkDayOverride.user_id == user_id,
                    WorkDayOverride.work_date >= date_from,
                    WorkDayOverride.work_date <= date_to,
                )
                .order_by(WorkDayOverride.work_date.asc())
            )
        )

    def get_override(self, *, user_id: int, work_date: date) -> WorkDayOverride | None:
        return self.db.scalar(
            select(WorkDayOverride).where(
                WorkDayOverride.user_id == user_id,
                WorkDayOverride.work_date == work_date,
            )
        )

    def delete_override(self, item: WorkDayOverride) -> None:
        self.db.delete(item)

    def list_contracts(self, *, user_id: int) -> list[EmploymentContract]:
        return list(
            self.db.scalars(
                select(EmploymentContract)
                .where(EmploymentContract.user_id == user_id)
                .order_by(EmploymentContract.effective_from.desc(), EmploymentContract.id.desc())
            )
        )

    def list_income_operations_with_categories(self, *, user_id: int) -> list[tuple[Operation, str]]:
        return [
            (operation, category_name)
            for operation, category_name in self.db.execute(
                select(Operation, Category.name)
                .join(Category, Category.id == Operation.category_id)
                .where(Operation.user_id == user_id, Operation.kind == "income")
                .order_by(Operation.operation_date.asc(), Operation.id.asc())
            )
        ]

    def get_contract(self, *, user_id: int, contract_id: int) -> EmploymentContract | None:
        return self.db.scalar(
            select(EmploymentContract).where(
                EmploymentContract.user_id == user_id,
                EmploymentContract.id == contract_id,
            )
        )

    def get_open_contract_before(self, *, user_id: int, effective_from: date) -> EmploymentContract | None:
        return self.db.scalar(
            select(EmploymentContract)
            .where(
                EmploymentContract.user_id == user_id,
                EmploymentContract.effective_to.is_(None),
                EmploymentContract.effective_from < effective_from,
            )
            .order_by(EmploymentContract.effective_from.desc(), EmploymentContract.id.desc())
            .limit(1)
        )

    def contracts_overlap(
        self,
        *,
        user_id: int,
        effective_from: date,
        effective_to: date | None,
        exclude_id: int | None = None,
    ) -> bool:
        # Employment periods may touch at a transition date: the outgoing
        # period ends on the same date the new one begins. A real overlap
        # therefore requires both boundaries to cross strictly.
        stmt = select(EmploymentContract.id).where(
            EmploymentContract.user_id == user_id,
            EmploymentContract.effective_from < (effective_to or date.max),
            and_(
                EmploymentContract.effective_to.is_(None)
                | (EmploymentContract.effective_to > effective_from)
            ),
        )
        if exclude_id:
            stmt = stmt.where(EmploymentContract.id != exclude_id)
        return self.db.scalar(stmt.limit(1)) is not None
