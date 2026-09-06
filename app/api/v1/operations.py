from datetime import date

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.operation import (
    CatalogProductCreate,
    CatalogProductDetachIn,
    CatalogProductDetachOut,
    CatalogProductListOut,
    CatalogProductMergeCandidateListOut,
    CatalogProductMergeIn,
    CatalogProductMergeOut,
    CatalogProductOut,
    CatalogProductSourceCreate,
    CatalogProductUpdate,
    ItemBrandCreate,
    ItemBrandListOut,
    ItemBrandMergeIn,
    ItemBrandMergeOut,
    ItemBrandOut,
    ItemBrandUpdate,
    ItemSourceCreate,
    ItemSourceListOut,
    ItemSourceOut,
    ItemSourceUpdate,
    MoneyFlowListOut,
    OperationCreate,
    OperationItemTemplateCreate,
    OperationItemTemplateBulkBrandUpdateIn,
    OperationItemTemplateBulkBrandUpdateOut,
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
from app.services.catalog_media_service import (
    CatalogMediaService,
    CatalogMediaTooLargeError,
    CatalogMediaValidationError,
)
from app.services.catalog_product_service import CatalogProductService
from app.services.item_brand_service import ItemBrandService
from app.services.item_source_service import ItemSourceService
from app.services.operation_service import OperationService

router = APIRouter(prefix="/operations", tags=["operations"])


def _dump_receipt_item(item) -> dict:
    data = item.model_dump()
    fields_set = getattr(item, "model_fields_set", set())
    for optional_link in ("template_id", "product_id", "brand_id", "source_id"):
        if optional_link not in fields_set:
            data.pop(optional_link, None)
    return data


def _read_catalog_image(file: UploadFile) -> bytes:
    raw = file.file.read(CatalogMediaService.MAX_UPLOAD_BYTES + 1)
    if len(raw) > CatalogMediaService.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file must be at most 8 MiB",
        )
    return raw


def _upload_catalog_image(*, db: Session, user_id: int, owner_kind: str, owner_id: int, file: UploadFile):
    try:
        return CatalogMediaService(db).upload(
            user_id=user_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
            content_type=file.content_type,
            raw=_read_catalog_image(file),
        )
    except CatalogMediaTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except CatalogMediaValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _delete_catalog_image(*, db: Session, user_id: int, owner_kind: str, owner_id: int):
    try:
        return CatalogMediaService(db).delete(
            user_id=user_id,
            owner_kind=owner_kind,
            owner_id=owner_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
    brand_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
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
            brand_id=brand_id,
            product_id=product_id,
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
    category_id: int | None = Query(default=None),
    item_template_id: int | None = Query(default=None),
    brand_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
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
            category_id=category_id,
            item_template_id=item_template_id,
            brand_id=brand_id,
            product_id=product_id,
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
    brand_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
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
            brand_id=brand_id,
            product_id=product_id,
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
    category_id: int | None = Query(default=None),
    item_template_id: int | None = Query(default=None),
    brand_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
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
            category_id=category_id,
            item_template_id=item_template_id,
            brand_id=brand_id,
            product_id=product_id,
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
            fx_rate_source=payload.fx_rate_source,
            fx_bank_code=payload.fx_bank_code,
            fx_bank_channel=payload.fx_bank_channel,
            fx_rate_kind=payload.fx_rate_kind,
            fx_manual_rate=payload.fx_manual_rate,
            fx_payment_mode=payload.fx_payment_mode,
            operation_date=payload.operation_date,
            category_id=payload.category_id,
            note=payload.note,
            receipt_items=[_dump_receipt_item(item) for item in payload.receipt_items],
            fx_settlement=payload.fx_settlement.model_dump() if payload.fx_settlement else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/catalog-products", response_model=CatalogProductListOut)
def list_catalog_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    q: str | None = Query(default=None, max_length=160),
    brand_id: int | None = Query(default=None, ge=1),
    category_id: int | None = Query(default=None, ge=1),
    include_archived: bool = Query(default=False),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items, total = CatalogProductService(db).list(
        user_id=user_id,
        page=page,
        page_size=page_size,
        q=q,
        brand_id=brand_id,
        category_id=category_id,
        include_archived=include_archived,
    )
    return CatalogProductListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/catalog-products",
    response_model=CatalogProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_catalog_product(
    payload: CatalogProductCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return CatalogProductService(db).create(
            user_id=user_id,
            name=payload.name,
            brand_id=payload.brand_id,
            category_id=payload.category_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/catalog-products/merge-candidates",
    response_model=CatalogProductMergeCandidateListOut,
)
def list_catalog_product_merge_candidates(
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items, total = CatalogProductService(db).list_merge_candidates(
        user_id=user_id,
        limit=limit,
    )
    return CatalogProductMergeCandidateListOut(items=items, total=total)


@router.get("/catalog-products/{product_id}", response_model=CatalogProductOut)
def get_catalog_product(
    product_id: int,
    include_archived: bool = Query(default=False),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return CatalogProductService(db).get(
            user_id=user_id,
            product_id=product_id,
            include_archived=include_archived,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/catalog-products/{product_id}/offers", response_model=OperationItemTemplateOut, status_code=status.HTTP_201_CREATED)
def add_catalog_product_source(
    product_id: int,
    payload: CatalogProductSourceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return OperationService(db).item_templates.add_product_source(
            user_id=user_id, product_id=product_id, **payload.model_dump(),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/catalog-products/{product_id}", response_model=CatalogProductOut)
def update_catalog_product(
    product_id: int,
    payload: CatalogProductUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    try:
        return CatalogProductService(db).update(
            user_id=user_id,
            product_id=product_id,
            updates=updates,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/catalog-products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_catalog_product(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        CatalogProductService(db).archive(
            user_id=user_id,
            product_id=product_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/catalog-products/{product_id}/merge",
    response_model=CatalogProductMergeOut,
)
def merge_catalog_products(
    product_id: int,
    payload: CatalogProductMergeIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return CatalogProductService(db).merge(
            user_id=user_id,
            target_product_id=product_id,
            source_product_ids=payload.source_product_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/catalog-products/{product_id}/offers/{template_id}/detach",
    response_model=CatalogProductDetachOut,
)
def detach_catalog_product_offer(
    product_id: int,
    template_id: int,
    payload: CatalogProductDetachIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return CatalogProductService(db).detach_offer(
            user_id=user_id,
            product_id=product_id,
            offer_id=template_id,
            updates=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/catalog-products/{product_id}/image",
    response_model=CatalogProductOut,
)
def upload_catalog_product_image(
    product_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _upload_catalog_image(
        db=db,
        user_id=user_id,
        owner_kind="product",
        owner_id=product_id,
        file=file,
    )
    return CatalogProductService(db).get(user_id=user_id, product_id=product_id)


@router.delete(
    "/catalog-products/{product_id}/image",
    response_model=CatalogProductOut,
)
def delete_catalog_product_image(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _delete_catalog_image(
        db=db,
        user_id=user_id,
        owner_kind="product",
        owner_id=product_id,
    )
    return CatalogProductService(db).get(user_id=user_id, product_id=product_id)


@router.get("/item-templates", response_model=OperationItemTemplateListOut)
def list_operation_item_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=120),
    brand_id: int | None = Query(default=None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    items, total = service.list_item_templates(
        user_id=user_id,
        page=page,
        page_size=page_size,
        q=q,
        brand_id=brand_id,
    )
    return OperationItemTemplateListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/media/{asset_id}/{variant}")
def get_catalog_media(
    asset_id: int,
    variant: str,
    if_none_match: str | None = Header(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        payload, checksum = CatalogMediaService(db).get_variant(
            user_id=user_id,
            asset_id=asset_id,
            variant=variant,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    etag = f'"{checksum}-{variant}"'
    headers = {
        "Cache-Control": "private, max-age=31536000, immutable",
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
    }
    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=payload, media_type="image/webp", headers=headers)


@router.get("/item-sources", response_model=ItemSourceListOut)
def list_item_sources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    q: str | None = Query(default=None, max_length=160),
    include_archived: bool = Query(default=False),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items, total = ItemSourceService(db).list(
        user_id=user_id,
        page=page,
        page_size=page_size,
        q=q,
        include_archived=include_archived,
    )
    return ItemSourceListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/item-sources", response_model=ItemSourceOut, status_code=status.HTTP_201_CREATED)
def create_item_source(
    payload: ItemSourceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ItemSourceService(db).create(user_id=user_id, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/item-sources/{source_id}", response_model=ItemSourceOut)
def get_item_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ItemSourceService(db).get(user_id=user_id, source_id=source_id, include_archived=True)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/item-sources/{source_id}", response_model=ItemSourceOut)
def update_item_source(
    source_id: int,
    payload: ItemSourceUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    try:
        return ItemSourceService(db).update(user_id=user_id, source_id=source_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/item-sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_item_source(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        ItemSourceService(db).archive(user_id=user_id, source_id=source_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/item-sources/{source_id}/image", response_model=ItemSourceOut)
def upload_item_source_image(
    source_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _upload_catalog_image(
        db=db,
        user_id=user_id,
        owner_kind="source",
        owner_id=source_id,
        file=file,
    )
    return ItemSourceService(db).get(user_id=user_id, source_id=source_id)


@router.delete("/item-sources/{source_id}/image", response_model=ItemSourceOut)
def delete_item_source_image(
    source_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _delete_catalog_image(db=db, user_id=user_id, owner_kind="source", owner_id=source_id)
    return ItemSourceService(db).get(user_id=user_id, source_id=source_id)


@router.get("/item-brands", response_model=ItemBrandListOut)
def list_item_brands(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    q: str | None = Query(default=None, max_length=160),
    include_archived: bool = Query(default=False),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items, total = ItemBrandService(db).list(
        user_id=user_id,
        page=page,
        page_size=page_size,
        q=q,
        include_archived=include_archived,
    )
    return ItemBrandListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/item-brands", response_model=ItemBrandOut, status_code=status.HTTP_201_CREATED)
def create_item_brand(
    payload: ItemBrandCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return ItemBrandService(db).create(
            user_id=user_id,
            name=payload.name,
            accent_color=payload.accent_color,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/item-brands/{brand_id}", response_model=ItemBrandOut)
def get_item_brand(
    brand_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        # Archived brands remain a valid historical dimension. Keep their detail
        # readable even though they are omitted from active selectors and cannot
        # be edited until explicitly restored.
        return ItemBrandService(db).get(user_id=user_id, brand_id=brand_id, include_archived=True)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/item-brands/{brand_id}", response_model=ItemBrandOut)
def update_item_brand(
    brand_id: int,
    payload: ItemBrandUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    try:
        return ItemBrandService(db).update(user_id=user_id, brand_id=brand_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/item-brands/{brand_id}/merge", response_model=ItemBrandMergeOut)
def merge_item_brand(
    brand_id: int,
    payload: ItemBrandMergeIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        brand, reassigned = ItemBrandService(db).merge(
            user_id=user_id,
            source_brand_id=brand_id,
            target_brand_id=payload.target_brand_id,
        )
        return ItemBrandMergeOut(brand=brand, reassigned_positions=reassigned)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/item-brands/{brand_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_item_brand(
    brand_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        ItemBrandService(db).archive(user_id=user_id, brand_id=brand_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/item-brands/{brand_id}/image", response_model=ItemBrandOut)
def upload_item_brand_image(
    brand_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _upload_catalog_image(
        db=db,
        user_id=user_id,
        owner_kind="brand",
        owner_id=brand_id,
        file=file,
    )
    return ItemBrandService(db).get(user_id=user_id, brand_id=brand_id)


@router.delete("/item-brands/{brand_id}/image", response_model=ItemBrandOut)
def delete_item_brand_image(
    brand_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _delete_catalog_image(db=db, user_id=user_id, owner_kind="brand", owner_id=brand_id)
    return ItemBrandService(db).get(user_id=user_id, brand_id=brand_id)


@router.post("/item-templates/bulk-brand", response_model=OperationItemTemplateBulkBrandUpdateOut)
def bulk_update_operation_item_template_brand(
    payload: OperationItemTemplateBulkBrandUpdateIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        updated = service.bulk_update_item_template_brand(
            user_id=user_id,
            template_ids=payload.template_ids,
            brand_id=payload.brand_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return OperationItemTemplateBulkBrandUpdateOut(updated=updated)


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


@router.delete(
    "/item-templates/{template_id}/prices/{price_id}",
    response_model=OperationItemTemplateOut,
)
def delete_operation_item_template_price(
    template_id: int,
    price_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.delete_item_template_price(
            user_id=user_id,
            template_id=template_id,
            price_id=price_id,
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
            product_id=payload.product_id,
            shop_name=payload.shop_name,
            source_id=payload.source_id,
            name=payload.name,
            last_category_id=payload.last_category_id,
            brand_id=payload.brand_id,
            latest_unit_price=payload.latest_unit_price,
            latest_price_date=payload.latest_price_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/item-templates/{template_id}", response_model=OperationItemTemplateOut)
def get_operation_item_template(
    template_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return OperationService(db).item_templates.get_item_template(
            user_id=user_id,
            template_id=template_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/item-templates/{template_id}/image", response_model=OperationItemTemplateOut)
def upload_operation_item_template_image(
    template_id: int,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _upload_catalog_image(
        db=db,
        user_id=user_id,
        owner_kind="template",
        owner_id=template_id,
        file=file,
    )
    return OperationService(db).item_templates.get_item_template(user_id=user_id, template_id=template_id)


@router.delete("/item-templates/{template_id}/image", response_model=OperationItemTemplateOut)
def delete_operation_item_template_image(
    template_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _delete_catalog_image(db=db, user_id=user_id, owner_kind="template", owner_id=template_id)
    return OperationService(db).item_templates.get_item_template(user_id=user_id, template_id=template_id)


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
    if "receipt_items" in payload.model_fields_set and payload.receipt_items is not None:
        updates["receipt_items"] = [_dump_receipt_item(item) for item in payload.receipt_items]
    if "fx_settlement" in updates and updates["fx_settlement"] is not None and hasattr(updates["fx_settlement"], "model_dump"):
        updates["fx_settlement"] = updates["fx_settlement"].model_dump()

    service = OperationService(db)
    try:
        return service.update_operation(user_id=user_id, operation_id=operation_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{operation_id}/restore", response_model=OperationOut)
def restore_operation(
    operation_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    try:
        return service.restore_deleted_operation(user_id=user_id, operation_id=operation_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


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
