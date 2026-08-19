from datetime import date

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    Category,
    EmploymentContract,
    Operation,
    PlanOperation,
    WorkDayOverride,
    WorkPaymentLink,
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

    def list_payment_links(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
    ) -> list:
        stmt = (
            select(WorkPaymentLink, Operation, Category)
            .outerjoin(
                Operation,
                and_(
                    Operation.id == WorkPaymentLink.operation_id,
                    Operation.user_id == user_id,
                ),
            )
            .outerjoin(Category, Category.id == Operation.category_id)
            .where(
                WorkPaymentLink.user_id == user_id,
                or_(
                    and_(
                        Operation.id.is_not(None),
                        Operation.operation_date >= date_from,
                        Operation.operation_date <= date_to,
                    ),
                    and_(
                        Operation.id.is_(None),
                        WorkPaymentLink.snapshot_operation_date >= date_from,
                        WorkPaymentLink.snapshot_operation_date <= date_to,
                    ),
                ),
            )
            .order_by(
                func.coalesce(
                    Operation.operation_date,
                    WorkPaymentLink.snapshot_operation_date,
                ).desc(),
                WorkPaymentLink.id.desc(),
            )
        )
        return list(self.db.execute(stmt).all())

    def list_income_payment_candidates(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
        q: str | None,
        limit: int,
    ) -> tuple[list, int]:
        conditions = [
            Operation.user_id == user_id,
            Operation.kind == "income",
            Operation.operation_date >= date_from,
            Operation.operation_date <= date_to,
        ]
        normalized_q = (q or "").strip()
        if normalized_q:
            pattern = f"%{normalized_q}%"
            conditions.append(
                or_(
                    Operation.note.ilike(pattern),
                    Category.name.ilike(pattern),
                    Operation.currency.ilike(pattern),
                )
            )
        total = int(
            self.db.scalar(
                select(func.count(Operation.id))
                .select_from(Operation)
                .outerjoin(Category, Category.id == Operation.category_id)
                .where(*conditions)
            )
            or 0
        )
        rows = list(
            self.db.execute(
                select(Operation, Category, WorkPaymentLink)
                .outerjoin(Category, Category.id == Operation.category_id)
                .outerjoin(
                    WorkPaymentLink,
                    and_(
                        WorkPaymentLink.user_id == user_id,
                        or_(
                            WorkPaymentLink.operation_id == Operation.id,
                            WorkPaymentLink.snapshot_operation_id == Operation.id,
                        ),
                    ),
                )
                .where(*conditions)
                .order_by(Operation.operation_date.desc(), Operation.id.desc())
                .limit(limit)
            ).all()
        )
        return rows, total

    def list_unlinked_payroll_income_operations(
        self,
        *,
        user_id: int,
        category_ids: list[int],
        date_from: date,
        date_to: date,
        received_through: date,
    ) -> list:
        """Return display-only income operations from the current payroll categories.

        These rows are deliberately not turned into ``WorkPaymentLink`` records.
        A payroll category can contain salary, advance, bonuses, vacation pay, and
        corrections, so these facts must stay role-neutral.
        """
        normalized_category_ids = sorted({int(category_id) for category_id in category_ids})
        if not normalized_category_ids:
            return []
        linked_operation = exists(
            select(WorkPaymentLink.id).where(
                WorkPaymentLink.user_id == user_id,
                or_(
                    WorkPaymentLink.operation_id == Operation.id,
                    WorkPaymentLink.snapshot_operation_id == Operation.id,
                ),
            )
        )
        stmt = (
            select(Operation, Category)
            .join(Category, Category.id == Operation.category_id)
            .where(
                Operation.user_id == user_id,
                Operation.kind == "income",
                Operation.category_id.in_(normalized_category_ids),
                Operation.operation_date >= date_from,
                Operation.operation_date <= date_to,
                Operation.operation_date <= received_through,
                ~linked_operation,
            )
            .order_by(Operation.operation_date.asc(), Operation.id.asc())
        )
        return list(self.db.execute(stmt).all())

    def get_operation_with_category(self, *, user_id: int, operation_id: int):
        return self.db.execute(
            select(Operation, Category)
            .outerjoin(Category, Category.id == Operation.category_id)
            .where(Operation.user_id == user_id, Operation.id == operation_id)
        ).first()

    def get_payment_link(self, *, user_id: int, link_id: int) -> WorkPaymentLink | None:
        return self.db.scalar(
            select(WorkPaymentLink).where(
                WorkPaymentLink.user_id == user_id,
                WorkPaymentLink.id == link_id,
            )
        )

    def get_payment_link_by_operation(
        self,
        *,
        user_id: int,
        operation_id: int,
    ) -> WorkPaymentLink | None:
        return self.db.scalar(
            select(WorkPaymentLink).where(
                WorkPaymentLink.user_id == user_id,
                or_(
                    WorkPaymentLink.operation_id == operation_id,
                    WorkPaymentLink.snapshot_operation_id == operation_id,
                ),
            )
        )

    def create_payment_link(self, **values) -> WorkPaymentLink:
        item = WorkPaymentLink(**values)
        self.db.add(item)
        self.db.flush()
        return item

    def delete_payment_link(self, item: WorkPaymentLink) -> None:
        self.db.delete(item)

    def payment_role_for_plan(self, *, user_id: int, plan_id: int) -> str | None:
        profile = self.get_profile(user_id=user_id)
        if not profile:
            return None
        if profile.salary_plan_id == plan_id:
            return "salary"
        if profile.advance_plan_id == plan_id:
            return "advance"
        return None

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
