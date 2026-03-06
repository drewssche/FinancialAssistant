from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_summary_cache
from app.repositories.operation_repo import OperationRepository


class OperationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)

    def create_operation(
        self,
        user_id: int,
        kind: str,
        amount: Decimal,
        operation_date: date,
        category_id: int | None,
        note: str | None,
    ):
        self._validate_kind(kind)
        item = self.repo.create(user_id, kind, amount, operation_date, category_id, note)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        self.db.refresh(item)
        return item

    def list_operations(
        self,
        user_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
    ) -> tuple[list, int]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if kind:
            self._validate_kind(kind)

        return self.repo.list_filtered(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
        )

    def get_operation(self, user_id: int, operation_id: int):
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")
        return item

    def update_operation(self, user_id: int, operation_id: int, updates: dict):
        if "kind" in updates and updates["kind"] is not None:
            self._validate_kind(updates["kind"])

        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        item = self.repo.update(item, updates)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        self.db.refresh(item)
        return item

    def delete_operation(self, user_id: int, operation_id: int) -> None:
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        self.repo.delete(item)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)

    @staticmethod
    def _validate_kind(kind: str) -> None:
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")
