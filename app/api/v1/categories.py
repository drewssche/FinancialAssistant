from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryGroupCreate, CategoryGroupOut, CategoryGroupUpdate, CategoryOut, CategoryUpdate
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    rows = service.list_categories(user_id)
    return [CategoryOut(**row) for row in rows]


@router.post("", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    try:
        created = service.create_category(
            user_id=user_id,
            name=payload.name,
            kind=payload.kind,
            group_id=payload.group_id,
            icon=payload.icon,
        )
        return CategoryOut(
            id=created.id,
            name=created.name,
            icon=created.icon,
            kind=created.kind,
            group_id=created.group_id,
            is_system=created.is_system,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/groups", response_model=list[CategoryGroupOut])
def list_category_groups(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    return service.list_groups(user_id)


@router.post("/groups", response_model=CategoryGroupOut)
def create_category_group(
    payload: CategoryGroupCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    try:
        return service.create_group(
            user_id=user_id,
            name=payload.name,
            kind=payload.kind,
            accent_color=payload.accent_color,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_category_group(
    group_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    try:
        service.delete_group(user_id=user_id, group_id=group_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/groups/{group_id}", response_model=CategoryGroupOut)
def update_category_group(
    group_id: int,
    payload: CategoryGroupUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    service = CategoryService(db)
    try:
        updated = service.update_group(user_id=user_id, group_id=group_id, updates=updates)
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_category(
    category_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    try:
        service.delete_category(user_id=user_id, category_id=category_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    service = CategoryService(db)
    try:
        updated = service.update_category(user_id=user_id, category_id=category_id, updates=updates)
        return CategoryOut(
            id=updated.id,
            name=updated.name,
            icon=updated.icon,
            kind=updated.kind,
            group_id=updated.group_id,
            is_system=updated.is_system,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
