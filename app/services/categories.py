from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.taxonomy import DEFAULT_GROUPED_CATEGORIES
from app.models.category import Category, CategoryGroup
from app.models.operation import Operation


def seed_default_categories(db: Session) -> None:
    group_map: dict[tuple[str, str], CategoryGroup] = {}
    existing_groups = list(db.scalars(select(CategoryGroup)).all())
    for group in existing_groups:
        group_map[(group.kind, group.name)] = group

    for kind, groups in DEFAULT_GROUPED_CATEGORIES.items():
        for group_idx, group_cfg in enumerate(groups):
            group_name = str(group_cfg["name"])
            group_color = str(group_cfg.get("color") or "#7aa7ff")
            group_icon = str(group_cfg.get("icon") or "📁")
            group = group_map.get((kind, group_name))
            if group is None:
                group = CategoryGroup(
                    kind=kind,
                    name=group_name,
                    color=group_color,
                    icon=group_icon,
                    sort_order=group_idx,
                    is_system=True,
                    is_archived=False,
                )
                db.add(group)
                db.flush()
                group_map[(kind, group_name)] = group
            else:
                group.is_system = True
                if not group.icon:
                    group.icon = group_icon

            names = [str(name) for name in group_cfg.get("categories", [])]
            existing_categories = {
                item.name: item
                for item in db.scalars(select(Category).where(Category.kind == kind)).all()
            }
            for category_idx, category_name in enumerate(names):
                existing = existing_categories.get(category_name)
                if existing:
                    existing.is_system = True
                    continue

                db.add(
                    Category(
                        kind=kind,
                        group_id=group.id,
                        name=category_name,
                        icon="",
                        sort_order=category_idx,
                        is_system=True,
                        is_archived=False,
                    )
                )

    db.commit()


def get_category_map(db: Session) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"income": [], "expense": []}
    rows = db.execute(
        select(Category.kind, Category.name)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id, isouter=True)
        .where(Category.is_archived.is_(False))
        .where((CategoryGroup.id.is_(None)) | (CategoryGroup.is_archived.is_(False)))
        .order_by(Category.kind.asc(), CategoryGroup.sort_order.asc(), Category.sort_order.asc(), Category.name.asc())
    ).all()
    for kind, name in rows:
        out.setdefault(kind, []).append(name)
    return out


def ensure_default_categories(db: Session) -> None:
    """Backward-compatible alias. Prefer `seed_default_categories` in startup/seed flows."""
    seed_default_categories(db)


def list_categories(db: Session, kind: str) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.kind == kind, Category.is_archived.is_(False))
            .order_by(Category.sort_order.asc(), Category.name.asc())
        ).all()
    )


def list_category_groups(db: Session, kind: str) -> list[CategoryGroup]:
    return list(
        db.scalars(
            select(CategoryGroup)
            .where(CategoryGroup.kind == kind, CategoryGroup.is_archived.is_(False))
            .order_by(CategoryGroup.sort_order.asc(), CategoryGroup.name.asc())
        ).all()
    )


def count_active_groups(db: Session, kind: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CategoryGroup)
            .where(CategoryGroup.kind == kind, CategoryGroup.is_archived.is_(False))
        )
        or 0
    )


def get_category_group(db: Session, group_id: UUID) -> CategoryGroup | None:
    return db.get(CategoryGroup, group_id)


def create_category_group(db: Session, kind: str, name: str, color: str, icon: str = "📁") -> CategoryGroup:
    max_sort = db.scalar(select(func.max(CategoryGroup.sort_order)).where(CategoryGroup.kind == kind))
    group = CategoryGroup(
        kind=kind,
        name=name,
        color=color,
        icon=icon,
        sort_order=int(max_sort or 0) + 1,
        is_system=False,
        is_archived=False,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_category_group(
    db: Session,
    item: CategoryGroup,
    *,
    name: str | None = None,
    color: str | None = None,
    icon: str | None = None,
    is_archived: bool | None = None,
) -> CategoryGroup:
    if name is not None:
        item.name = name
    if color is not None:
        item.color = color
    if icon is not None:
        item.icon = icon
    if is_archived is not None:
        item.is_archived = is_archived
    db.commit()
    db.refresh(item)
    return item


def count_group_usage(db: Session, group: CategoryGroup) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Operation)
            .join(
                Category,
                (Category.kind == Operation.kind) & (Category.name == Operation.subcategory),
            )
            .where(Category.group_id == group.id)
        )
        or 0
    )


def count_group_categories(db: Session, group: CategoryGroup) -> int:
    return int(
        db.scalar(select(func.count()).select_from(Category).where(Category.group_id == group.id, Category.is_archived.is_(False)))
        or 0
    )


def count_all_group_categories(db: Session, group: CategoryGroup) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Category).where(Category.group_id == group.id)
        )
        or 0
    )


def remove_category_group(db: Session, group: CategoryGroup) -> None:
    db.execute(delete(CategoryGroup).where(CategoryGroup.id == group.id))
    db.commit()


def create_category(db: Session, kind: str, name: str, group_id: UUID | None = None, icon: str = "") -> Category:
    max_sort = db.scalar(select(func.max(Category.sort_order)).where(Category.kind == kind, Category.group_id == group_id))
    item = Category(
        kind=kind,
        name=name,
        group_id=group_id,
        icon=icon,
        sort_order=int(max_sort or 0) + 1,
        is_system=False,
        is_archived=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_category(db: Session, category_id: UUID) -> Category | None:
    return db.get(Category, category_id)


def rename_category(db: Session, item: Category, new_name: str) -> Category:
    old_name = item.name
    item.name = new_name
    db.execute(
        update(Operation)
        .where(Operation.kind == item.kind, Operation.subcategory == old_name)
        .values(subcategory=new_name)
    )
    db.commit()
    db.refresh(item)
    return item


def move_category_to_group(db: Session, item: Category, group_id: UUID | None) -> Category:
    item.group_id = group_id
    max_sort = db.scalar(
        select(func.max(Category.sort_order)).where(Category.kind == item.kind, Category.group_id == group_id)
    )
    item.sort_order = int(max_sort or 0) + 1
    db.commit()
    db.refresh(item)
    return item


def archive_category(db: Session, item: Category, is_archived: bool = True) -> Category:
    item.is_archived = is_archived
    db.commit()
    db.refresh(item)
    return item


def archive_category_group(db: Session, group: CategoryGroup, is_archived: bool = True) -> CategoryGroup:
    group.is_archived = is_archived
    db.execute(
        update(Category)
        .where(Category.group_id == group.id)
        .values(is_archived=is_archived)
    )
    db.commit()
    db.refresh(group)
    return group


def reorder_category_groups(db: Session, kind: str, ordered_group_ids: list[UUID]) -> None:
    rows = db.scalars(
        select(CategoryGroup)
        .where(CategoryGroup.kind == kind, CategoryGroup.is_archived.is_(False))
    ).all()
    by_id = {row.id: row for row in rows}
    unknown = [gid for gid in ordered_group_ids if gid not in by_id]
    if unknown:
        raise ValueError("invalid group ids")

    remaining = [row.id for row in rows if row.id not in ordered_group_ids]
    merged = ordered_group_ids + remaining
    for idx, group_id in enumerate(merged):
        by_id[group_id].sort_order = idx
    db.commit()


def bulk_reorder_categories(
    db: Session,
    kind: str,
    items: list[dict[str, Any]],
) -> None:
    rows = db.scalars(
        select(Category).where(Category.kind == kind, Category.is_archived.is_(False))
    ).all()
    by_id = {row.id: row for row in rows}

    for payload in items:
        row_id = payload["id"]
        item = by_id.get(row_id)
        if item is None:
            raise ValueError("invalid category ids")
        item.group_id = payload.get("group_id")
        item.sort_order = int(payload.get("sort_order", item.sort_order))

    db.commit()


def count_category_usage(db: Session, item: Category) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Operation)
            .where(Operation.kind == item.kind, Operation.subcategory == item.name)
        )
        or 0
    )


def remove_category(db: Session, item: Category) -> None:
    db.execute(delete(Category).where(Category.id == item.id))
    db.commit()


def serialize_category(item: Category) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "kind": item.kind,
        "group_id": str(item.group_id) if item.group_id else None,
        "name": item.name,
        "icon": item.icon,
        "sort_order": item.sort_order,
        "is_system": item.is_system,
        "is_archived": item.is_archived,
    }


def serialize_category_group(item: CategoryGroup) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "kind": item.kind,
        "name": item.name,
        "color": item.color,
        "icon": item.icon,
        "sort_order": item.sort_order,
        "is_system": item.is_system,
        "is_archived": item.is_archived,
    }


def grouped_categories_payload(db: Session, kind: str) -> list[dict[str, Any]]:
    groups = list_category_groups(db, kind)
    by_group: dict[UUID, list[Category]] = {group.id: [] for group in groups}
    items = db.scalars(
        select(Category)
        .where(Category.kind == kind, Category.is_archived.is_(False))
        .order_by(Category.sort_order.asc(), Category.name.asc())
    ).all()

    ungrouped: list[Category] = []
    for item in items:
        if item.group_id in by_group:
            by_group[item.group_id].append(item)
        else:
            ungrouped.append(item)

    result = [
        {
            **serialize_category_group(group),
            "categories": [serialize_category(item) for item in by_group[group.id]],
        }
        for group in groups
    ]
    result.insert(
        0,
        {
            "id": "__ungrouped__",
            "kind": kind,
            "name": "Без группы",
            "color": "#6f87a4",
            "icon": "📁",
            "sort_order": -1,
            "is_system": True,
            "is_archived": False,
            "is_virtual": True,
            "categories": [serialize_category(item) for item in ungrouped],
        },
    )
    return result
