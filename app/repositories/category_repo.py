from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, CategoryGroup


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: int):
        stmt = (
            select(
                Category.id,
                Category.name,
                Category.icon,
                Category.kind,
                Category.group_id,
                Category.is_system,
                CategoryGroup.name.label("group_name"),
                CategoryGroup.icon.label("group_icon"),
                CategoryGroup.accent_color.label("group_accent_color"),
            )
            .outerjoin(CategoryGroup, CategoryGroup.id == Category.group_id)
            .where((Category.user_id == user_id) | (Category.is_system.is_(True)))
            .order_by(Category.name)
        )
        return list(self.db.execute(stmt).mappings())

    def create(self, user_id: int, name: str, kind: str, group_id: int | None = None, icon: str | None = None) -> Category:
        category = Category(user_id=user_id, name=name, icon=icon, kind=kind, group_id=group_id, is_system=False)
        self.db.add(category)
        self.db.flush()
        return category

    def get_by_id_for_user(self, user_id: int, category_id: int) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.is_system.is_(False),
        )
        return self.db.scalar(stmt)

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.flush()

    def update(self, category: Category, updates: dict) -> Category:
        for key, value in updates.items():
            setattr(category, key, value)
        self.db.flush()
        return category

    def list_groups_for_user(self, user_id: int) -> list[CategoryGroup]:
        stmt = select(CategoryGroup).where(CategoryGroup.user_id == user_id).order_by(CategoryGroup.name)
        return list(self.db.scalars(stmt))

    def create_group(self, user_id: int, name: str, kind: str, accent_color: str | None) -> CategoryGroup:
        group = CategoryGroup(
            user_id=user_id,
            name=name,
            kind=kind,
            accent_color=accent_color,
        )
        self.db.add(group)
        self.db.flush()
        return group

    def get_group_by_id_for_user(self, user_id: int, group_id: int) -> CategoryGroup | None:
        stmt = select(CategoryGroup).where(CategoryGroup.id == group_id, CategoryGroup.user_id == user_id)
        return self.db.scalar(stmt)

    def clear_group_refs(self, user_id: int, group_id: int) -> None:
        categories = list(
            self.db.scalars(
                select(Category).where(Category.user_id == user_id, Category.group_id == group_id)
            )
        )
        for category in categories:
            category.group_id = None
        self.db.flush()

    def delete_group(self, group: CategoryGroup) -> None:
        self.db.delete(group)
        self.db.flush()

    def update_group(self, group: CategoryGroup, updates: dict) -> CategoryGroup:
        for key, value in updates.items():
            setattr(group, key, value)
        self.db.flush()
        return group
