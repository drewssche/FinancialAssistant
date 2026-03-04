from sqlalchemy.orm import Session

from app.repositories.category_repo import CategoryRepository


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoryRepository(db)

    def list_categories(self, user_id: int):
        return self.repo.list_for_user(user_id)

    def create_category(self, user_id: int, name: str, kind: str):
        category = self.repo.create(user_id=user_id, name=name, kind=kind)
        self.db.commit()
        self.db.refresh(category)
        return category
