from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int):
        stmt = select(Category).where((Category.user_id == user_id) | (Category.is_system.is_(True))).order_by(Category.name)
        return list(self.db.scalars(stmt))

    def create(self, user_id: int, name: str, kind: str) -> Category:
        category = Category(user_id=user_id, name=name, kind=kind, is_system=False)
        self.db.add(category)
        self.db.flush()
        return category
