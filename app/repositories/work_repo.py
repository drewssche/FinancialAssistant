from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models import EmploymentContract, PlanOperation, WorkDayOverride, WorkProfile


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
        stmt = select(EmploymentContract.id).where(
            EmploymentContract.user_id == user_id,
            EmploymentContract.effective_from <= (effective_to or date.max),
            and_(
                EmploymentContract.effective_to.is_(None)
                | (EmploymentContract.effective_to >= effective_from)
            ),
        )
        if exclude_id:
            stmt = stmt.where(EmploymentContract.id != exclude_id)
        return self.db.scalar(stmt.limit(1)) is not None
