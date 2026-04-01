from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.operation import (
    MoneyFlowListOut,
    OperationCreate,
    OperationItemTemplateCreate,
    OperationItemTemplateDeleteAllOut,
    OperationItemPriceOut,
    OperationItemTemplateListOut,
    OperationItemTemplateOut,
    OperationItemTemplateUpdate,
    OperationListOut,
    OperationOut,
    OperationSummaryOut,
    OperationUpdate,
)
from app.services.operation_service import OperationService

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("", response_model=OperationListOut)
def list_operations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="operation_date", pattern="^(operation_date|amount|created_at)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    kind: str | None = Query(default=None, pattern="^(income|expense)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_id: int | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    quick_view: str | None = Query(default=None, pattern="^(all|receipt|large|uncategorized)$"),
    currency_scope: str | None = Query(default=None, pattern="^(all|base|foreign)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        items, total = service.list_operations(
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
            quick_view=quick_view,
            currency_scope=currency_scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OperationListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/money-flow", response_model=MoneyFlowListOut)
def list_money_flow(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="operation_date", pattern="^(operation_date|amount|created_at)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    direction: str | None = Query(default=None, pattern="^(all|inflow|outflow)$"),
    source: str | None = Query(default=None, pattern="^(all|operation|debt|fx)$"),
    currency_scope: str | None = Query(default=None, pattern="^(all|base|foreign)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        items, total = service.list_money_flow(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return MoneyFlowListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary", response_model=OperationSummaryOut)
def summarize_operations(
    kind: str | None = Query(default=None, pattern="^(income|expense)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    category_id: int | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    quick_view: str | None = Query(default=None, pattern="^(all|receipt|large|uncategorized)$"),
    currency_scope: str | None = Query(default=None, pattern="^(all|base|foreign)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.summarize_operations(
            user_id=user_id,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            quick_view=quick_view,
            currency_scope=currency_scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/money-flow/summary", response_model=OperationSummaryOut)
def summarize_money_flow(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    direction: str | None = Query(default=None, pattern="^(all|inflow|outflow)$"),
    source: str | None = Query(default=None, pattern="^(all|operation|debt|fx)$"),
    currency_scope: str | None = Query(default=None, pattern="^(all|base|foreign)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.summarize_money_flow(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("", response_model=OperationOut, status_code=status.HTTP_201_CREATED)
def create_operation(
    payload: OperationCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.create_operation(
            user_id=user_id,
            kind=payload.kind,
            amount=payload.amount,
            currency=payload.currency,
            fx_rate=payload.fx_rate,
            operation_date=payload.operation_date,
            category_id=payload.category_id,
            note=payload.note,
            receipt_items=[item.model_dump() for item in payload.receipt_items],
            fx_settlement=payload.fx_settlement.model_dump() if payload.fx_settlement else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/item-templates", response_model=OperationItemTemplateListOut)
def list_operation_item_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=120),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    items, total = service.list_item_templates(
        user_id=user_id,
        page=page,
        page_size=page_size,
        q=q,
    )
    return OperationItemTemplateListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/item-templates/{template_id}/prices", response_model=list[OperationItemPriceOut])
def list_operation_item_template_prices(
    template_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.list_item_template_prices(
            user_id=user_id,
            template_id=template_id,
            limit=limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/item-templates", response_model=OperationItemTemplateOut, status_code=status.HTTP_201_CREATED)
def create_operation_item_template(
    payload: OperationItemTemplateCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.create_item_template(
            user_id=user_id,
            shop_name=payload.shop_name,
            name=payload.name,
            latest_unit_price=payload.latest_unit_price,
            latest_price_date=payload.latest_price_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/item-templates/{template_id}", response_model=OperationItemTemplateOut)
def update_operation_item_template(
    template_id: int,
    payload: OperationItemTemplateUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    service = OperationService(db)
    try:
        return service.update_item_template(
            user_id=user_id,
            template_id=template_id,
            updates=updates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/item-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_operation_item_template(
    template_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        service.delete_item_template(user_id=user_id, template_id=template_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/item-templates", response_model=OperationItemTemplateDeleteAllOut)
def delete_all_operation_item_templates(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    deleted = service.delete_all_item_templates(user_id=user_id)
    return OperationItemTemplateDeleteAllOut(deleted=deleted)


@router.get("/{operation_id}", response_model=OperationOut)
def get_operation(
    operation_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.get_operation(user_id=user_id, operation_id=operation_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{operation_id}", response_model=OperationOut)
def update_operation(
    operation_id: int,
    payload: OperationUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    if "receipt_items" in updates and updates["receipt_items"] is not None:
        updates["receipt_items"] = [item.model_dump() if hasattr(item, "model_dump") else item for item in updates["receipt_items"]]
    if "fx_settlement" in updates and updates["fx_settlement"] is not None and hasattr(updates["fx_settlement"], "model_dump"):
        updates["fx_settlement"] = updates["fx_settlement"].model_dump()

    service = OperationService(db)
    try:
        return service.update_operation(user_id=user_id, operation_id=operation_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_operation(
    operation_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        service.delete_operation(user_id=user_id, operation_id=operation_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
