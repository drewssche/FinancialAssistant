from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.taxonomy import DEFAULT_ACCOUNTS
from app.db.session import get_db
from app.models.category import Category, CategoryGroup
from app.services.categories import (
    archive_category,
    archive_category_group,
    bulk_reorder_categories,
    count_category_usage,
    count_active_groups,
    count_all_group_categories,
    count_group_categories,
    count_group_usage,
    create_category,
    create_category_group,
    get_category,
    get_category_group,
    get_category_map,
    grouped_categories_payload,
    list_categories,
    move_category_to_group,
    remove_category,
    remove_category_group,
    rename_category,
    serialize_category,
    serialize_category_group,
    update_category_group,
    reorder_category_groups,
)
from app.services.operations import (
    build_summary,
    create_operation,
    delete_operation,
    get_operation,
    recent_operations,
    serialize_operation,
    update_operation,
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()

ALLOWED_GROUP_ICONS = {
    "📁", "🏠", "🍽️", "💊", "🛍️", "🎉", "🎁", "💼",
    "✨", "🚗", "🏋️", "📚", "🧾", "💡", "📱", "🧰",
    "🧴", "☕", "✈️", "🎮", "💸", "🧘", "🩺", "🛒",
}


class CategoryCreatePayload(BaseModel):
    kind: str
    name: str
    group_id: UUID | None = None
    icon: str | None = None


class CategoryUpdatePayload(BaseModel):
    name: str | None = None
    group_id: UUID | None = None
    icon: str | None = None


class CategoryGroupCreatePayload(BaseModel):
    kind: str
    name: str
    color: str = "#7aa7ff"
    icon: str = "📁"


class CategoryGroupUpdatePayload(BaseModel):
    name: str | None = None
    color: str | None = None
    icon: str | None = None
    is_archived: bool | None = None


class ArchivePayload(BaseModel):
    is_archived: bool = True


class CategoryReorderItemPayload(BaseModel):
    id: UUID
    group_id: UUID | None
    sort_order: int


class CategoryReorderPayload(BaseModel):
    kind: str
    items: list[CategoryReorderItemPayload]


class GroupReorderPayload(BaseModel):
    kind: str
    group_ids: list[UUID]


def _normalize_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def _normalize_color(color: str) -> str:
    value = (color or "").strip().lower()
    if len(value) == 7 and value.startswith("#"):
        return value
    return "#7aa7ff"


def _normalize_icon(icon: str | None) -> str:
    value = (icon or "📁").strip()
    if value in ALLOWED_GROUP_ICONS:
        return value
    return "📁"


def _normalize_category_icon(icon: str | None) -> str:
    value = (icon or "").strip()
    if not value:
        return ""
    if value in ALLOWED_GROUP_ICONS:
        return value
    return ""


def _subcategory_allowed(db: Session, kind: str, subcategory: str) -> bool:
    stmt = (
        select(Category.id)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id, isouter=True)
        .where(
            Category.kind == kind,
            Category.name == subcategory,
            Category.is_archived.is_(False),
            (CategoryGroup.id.is_(None)) | (CategoryGroup.is_archived.is_(False)),
        )
    )
    return db.scalar(stmt) is not None


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    summary = build_summary(db, today, "day")
    recent = [serialize_operation(op) for op in recent_operations(db, 20)]
    category_map = get_category_map(db)
    try:
        asset_version = int(Path("static/app.js").stat().st_mtime)
    except OSError:
        asset_version = 1
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "today": today.isoformat(),
            "category_map": category_map,
            "accounts": DEFAULT_ACCOUNTS,
            "summary": summary,
            "recent_operations": recent,
            "asset_version": asset_version,
        },
    )


@router.get("/api/summary")
def summary(period: str = "day", selected_date: str | None = None, db: Session = Depends(get_db)):
    if period not in {"day", "week"}:
        return JSONResponse(status_code=400, content={"detail": "period must be day or week"})

    try:
        selected = date.fromisoformat(selected_date) if selected_date else date.today()
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "invalid selected_date"})

    data = build_summary(db, selected, period)
    return {"ok": True, "data": data}


@router.post("/api/operations")
def add_operation(
    kind: str = Form(...),
    subcategory: str = Form(...),
    amount: str = Form(...),
    occurred_on: str = Form(...),
    account: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    if not _subcategory_allowed(db, kind, subcategory):
        return JSONResponse(status_code=400, content={"detail": "invalid subcategory"})

    try:
        parsed_amount = Decimal(amount)
    except InvalidOperation:
        return JSONResponse(status_code=400, content={"detail": "invalid amount"})
    if parsed_amount <= 0:
        return JSONResponse(status_code=400, content={"detail": "amount must be > 0"})

    try:
        parsed_date = date.fromisoformat(occurred_on)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "invalid date"})

    op = create_operation(
        db,
        kind=kind,
        subcategory=subcategory,
        amount=parsed_amount.quantize(Decimal("0.01")),
        occurred_on=parsed_date,
        account=account,
        comment=comment.strip(),
    )
    return {"ok": True, "id": str(op.id)}


@router.get("/api/operations/{operation_id}")
def get_operation_by_id(operation_id: UUID, db: Session = Depends(get_db)):
    op = get_operation(db, operation_id)
    if not op:
        return JSONResponse(status_code=404, content={"detail": "operation not found"})
    return {"ok": True, "data": serialize_operation(op)}


@router.put("/api/operations/{operation_id}")
def edit_operation(
    operation_id: UUID,
    kind: str = Form(...),
    subcategory: str = Form(...),
    amount: str = Form(...),
    occurred_on: str = Form(...),
    account: str = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db),
):
    op = get_operation(db, operation_id)
    if not op:
        return JSONResponse(status_code=404, content={"detail": "operation not found"})

    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    if not _subcategory_allowed(db, kind, subcategory):
        return JSONResponse(status_code=400, content={"detail": "invalid subcategory"})

    try:
        parsed_amount = Decimal(amount)
    except InvalidOperation:
        return JSONResponse(status_code=400, content={"detail": "invalid amount"})
    if parsed_amount <= 0:
        return JSONResponse(status_code=400, content={"detail": "amount must be > 0"})

    try:
        parsed_date = date.fromisoformat(occurred_on)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "invalid date"})

    op = update_operation(
        db,
        op,
        kind=kind,
        subcategory=subcategory,
        amount=parsed_amount.quantize(Decimal("0.01")),
        occurred_on=parsed_date,
        account=account,
        comment=comment.strip(),
    )
    return {"ok": True, "id": str(op.id)}


@router.delete("/api/operations/{operation_id}")
def remove_operation(operation_id: UUID, db: Session = Depends(get_db)):
    op = get_operation(db, operation_id)
    if not op:
        return JSONResponse(status_code=404, content={"detail": "operation not found"})
    delete_operation(db, op)
    return {"ok": True}


@router.get("/api/categories")
def categories(kind: str, db: Session = Depends(get_db)):
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    items = [serialize_category(item) for item in list_categories(db, kind)]
    return {"ok": True, "data": items}


@router.get("/api/category-groups")
def category_groups(kind: str, db: Session = Depends(get_db)):
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    return {"ok": True, "data": grouped_categories_payload(db, kind)}


@router.post("/api/categories")
def add_category(payload: CategoryCreatePayload, db: Session = Depends(get_db)):
    kind = payload.kind
    name = _normalize_name(payload.name)
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    if len(name) < 2:
        return JSONResponse(status_code=400, content={"detail": "category name too short"})

    exists = db.scalar(
        select(Category.id).where(Category.kind == kind, Category.name == name, Category.is_archived.is_(False))
    )
    if exists:
        return JSONResponse(status_code=400, content={"detail": "category already exists"})

    if payload.group_id is not None:
        group = get_category_group(db, payload.group_id)
        if not group or group.kind != kind or group.is_archived:
            return JSONResponse(status_code=400, content={"detail": "invalid group"})

    item = create_category(db, kind, name, payload.group_id, _normalize_category_icon(payload.icon))
    return {"ok": True, "data": serialize_category(item)}


@router.post("/api/categories/reorder")
def reorder_categories(payload: CategoryReorderPayload, db: Session = Depends(get_db)):
    kind = payload.kind
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    try:
        bulk_reorder_categories(
            db,
            kind,
            [
                {"id": item.id, "group_id": item.group_id, "sort_order": item.sort_order}
                for item in payload.items
            ],
        )
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "invalid category ids"})
    return {"ok": True}


@router.put("/api/categories/{category_id}/archive")
def set_category_archive_state(category_id: UUID, payload: ArchivePayload, db: Session = Depends(get_db)):
    item = get_category(db, category_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "category not found"})

    if not payload.is_archived and item.group_id:
        group = get_category_group(db, item.group_id)
        if group and group.is_archived:
            return JSONResponse(status_code=400, content={"detail": "cannot unarchive category in archived group"})

    item = archive_category(db, item, payload.is_archived)
    return {"ok": True, "data": serialize_category(item)}


@router.post("/api/category-groups")
def add_category_group(payload: CategoryGroupCreatePayload, db: Session = Depends(get_db)):
    kind = payload.kind
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})

    name = _normalize_name(payload.name)
    if len(name) < 2:
        return JSONResponse(status_code=400, content={"detail": "group name too short"})

    duplicate = db.scalar(
        select(CategoryGroup.id).where(
            CategoryGroup.kind == kind,
            CategoryGroup.name == name,
            CategoryGroup.is_archived.is_(False),
        )
    )
    if duplicate:
        return JSONResponse(status_code=400, content={"detail": "group already exists"})

    item = create_category_group(
        db,
        kind,
        name,
        _normalize_color(payload.color),
        _normalize_icon(payload.icon),
    )
    return {"ok": True, "data": serialize_category_group(item)}


@router.post("/api/category-groups/reorder")
def reorder_groups(payload: GroupReorderPayload, db: Session = Depends(get_db)):
    kind = payload.kind
    if kind not in {"income", "expense"}:
        return JSONResponse(status_code=400, content={"detail": "invalid kind"})
    if not payload.group_ids:
        return JSONResponse(status_code=400, content={"detail": "empty group_ids"})
    try:
        reorder_category_groups(db, kind, payload.group_ids)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "invalid group ids"})
    return {"ok": True}


@router.put("/api/category-groups/{group_id}")
def edit_category_group(group_id: UUID, payload: CategoryGroupUpdatePayload, db: Session = Depends(get_db)):
    item = get_category_group(db, group_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "group not found"})

    next_name = None
    if payload.name is not None:
        next_name = _normalize_name(payload.name)
        if len(next_name) < 2:
            return JSONResponse(status_code=400, content={"detail": "group name too short"})

        duplicate = db.scalar(
            select(CategoryGroup.id).where(
                CategoryGroup.kind == item.kind,
                CategoryGroup.name == next_name,
                CategoryGroup.id != item.id,
                CategoryGroup.is_archived.is_(False),
            )
        )
        if duplicate:
            return JSONResponse(status_code=400, content={"detail": "group already exists"})

    next_color = _normalize_color(payload.color) if payload.color is not None else None
    next_icon = _normalize_icon(payload.icon) if payload.icon is not None else None
    item = update_category_group(
        db,
        item,
        name=next_name,
        color=next_color,
        icon=next_icon,
        is_archived=payload.is_archived,
    )
    return {"ok": True, "data": serialize_category_group(item)}


@router.delete("/api/category-groups/{group_id}")
def delete_category_group(group_id: UUID, db: Session = Depends(get_db)):
    item = get_category_group(db, group_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "group not found"})

    if count_group_usage(db, item) > 0:
        return JSONResponse(status_code=400, content={"detail": "cannot delete group with operations"})
    if count_all_group_categories(db, item) > 0:
        return JSONResponse(status_code=400, content={"detail": "cannot delete non-empty group"})

    remove_category_group(db, item)
    return {"ok": True}


@router.put("/api/category-groups/{group_id}/archive")
def set_group_archive_state(group_id: UUID, payload: ArchivePayload, db: Session = Depends(get_db)):
    item = get_category_group(db, group_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "group not found"})

    if payload.is_archived and count_active_groups(db, item.kind) <= 1:
        return JSONResponse(status_code=400, content={"detail": "cannot archive last active group"})

    item = archive_category_group(db, item, payload.is_archived)
    return {"ok": True, "data": serialize_category_group(item)}


@router.put("/api/categories/{category_id}")
def edit_category(category_id: UUID, payload: CategoryUpdatePayload, db: Session = Depends(get_db)):
    item = get_category(db, category_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "category not found"})

    if payload.name is not None:
        name = _normalize_name(payload.name)
        if len(name) < 2:
            return JSONResponse(status_code=400, content={"detail": "category name too short"})

        duplicate = db.scalar(
            select(Category.id).where(
                Category.kind == item.kind,
                Category.name == name,
                Category.id != item.id,
                Category.is_archived.is_(False),
            )
        )
        if duplicate:
            return JSONResponse(status_code=400, content={"detail": "category already exists"})
        item = rename_category(db, item, name)

    model_fields = payload.model_fields_set
    if "group_id" in model_fields:
        if payload.group_id is None:
            item = move_category_to_group(db, item, None)
        else:
            group = get_category_group(db, payload.group_id)
            if not group or group.kind != item.kind or group.is_archived:
                return JSONResponse(status_code=400, content={"detail": "invalid group"})
            item = move_category_to_group(db, item, payload.group_id)

    if "icon" in model_fields:
        item.icon = _normalize_category_icon(payload.icon)
        db.commit()
        db.refresh(item)

    return {"ok": True, "data": serialize_category(item)}


@router.delete("/api/categories/{category_id}")
def delete_category(category_id: UUID, db: Session = Depends(get_db)):
    item = get_category(db, category_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "category not found"})

    usage = count_category_usage(db, item)
    if usage > 0:
        return JSONResponse(
            status_code=400,
            content={"detail": "cannot delete category with operations"},
        )

    remove_category(db, item)
    return {"ok": True}
