from sqlalchemy.orm import Session

from app.repositories.category_repo import CategoryRepository


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoryRepository(db)

    def list_categories(self, user_id: int):
        return self.repo.list_for_user(user_id)

    def create_category(self, user_id: int, name: str, kind: str, group_id: int | None = None, icon: str | None = None):
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")
        if group_id is not None:
            group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=group_id)
            if not group:
                raise ValueError("Group not found")
            if group.kind != kind:
                raise ValueError("Group kind must match category kind")
        category = self.repo.create(user_id=user_id, name=name, kind=kind, group_id=group_id, icon=icon)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, user_id: int, category_id: int) -> None:
        category = self.repo.get_by_id_for_user(user_id=user_id, category_id=category_id)
        if not category:
            raise LookupError("Category not found")
        self.repo.delete(category)
        self.db.commit()

    def update_category(self, user_id: int, category_id: int, updates: dict):
        category = self.repo.get_by_id_for_user(user_id=user_id, category_id=category_id)
        if not category:
            raise LookupError("Category not found")

        kind = updates.get("kind", category.kind)
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")

        if "group_id" in updates and updates["group_id"] is not None:
            group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=updates["group_id"])
            if not group:
                raise ValueError("Group not found")
            if group.kind != kind:
                raise ValueError("Group kind must match category kind")

        if "name" in updates and not updates["name"]:
            raise ValueError("name must not be empty")

        category = self.repo.update(category, updates)
        self.db.commit()
        self.db.refresh(category)
        return category

    def list_groups(self, user_id: int):
        return self.repo.list_groups_for_user(user_id)

    def create_group(
        self,
        user_id: int,
        name: str,
        kind: str,
        accent_color: str | None = None,
    ):
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")
        group = self.repo.create_group(
            user_id=user_id,
            name=name,
            kind=kind,
            accent_color=accent_color,
        )
        self.db.commit()
        self.db.refresh(group)
        return group

    def update_group(self, user_id: int, group_id: int, updates: dict):
        group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=group_id)
        if not group:
            raise LookupError("Group not found")
        if "name" in updates and not updates["name"]:
            raise ValueError("name must not be empty")
        group = self.repo.update_group(group, updates)
        self.db.commit()
        self.db.refresh(group)
        return group

    def delete_group(self, user_id: int, group_id: int) -> None:
        group = self.repo.get_group_by_id_for_user(user_id=user_id, group_id=group_id)
        if not group:
            raise LookupError("Group not found")
        self.repo.clear_group_refs(user_id=user_id, group_id=group_id)
        self.repo.delete_group(group)
        self.db.commit()
