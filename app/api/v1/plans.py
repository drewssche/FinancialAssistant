from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.plan import PlanConfirmOut, PlanCreate, PlanEventListOut, PlanListOut, PlanOut, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=PlanListOut)
def list_plans(
    q: str | None = Query(default=None, max_length=100),
    kind: str | None = Query(default=None, pattern="^(income|expense)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        items, total = service.list_plans(user_id=user_id, q=q, kind=kind)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlanListOut(items=items, total=total)


@router.get("/history", response_model=PlanEventListOut)
def list_plan_history(
    q: str | None = Query(default=None, max_length=100),
    kind: str | None = Query(default=None, pattern="^(income|expense)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        items, total = service.list_history(user_id=user_id, q=q, kind=kind)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlanEventListOut(items=items, total=total)


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        return service.create_plan(
            user_id=user_id,
            kind=payload.kind,
            amount=payload.amount,
            scheduled_date=payload.scheduled_date,
            category_id=payload.category_id,
            note=payload.note,
            receipt_items=[item.model_dump() for item in payload.receipt_items],
            recurrence_enabled=payload.recurrence_enabled,
            recurrence_frequency=payload.recurrence_frequency,
            recurrence_interval=payload.recurrence_interval,
            recurrence_weekdays=payload.recurrence_weekdays,
            recurrence_workdays_only=payload.recurrence_workdays_only,
            recurrence_month_end=payload.recurrence_month_end,
            recurrence_end_date=payload.recurrence_end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        return service.get_plan(user_id=user_id, plan_id=plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    service = PlanService(db)
    try:
        return service.update_plan(user_id=user_id, plan_id=plan_id, updates=updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{plan_id}/confirm", response_model=PlanConfirmOut)
def confirm_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        return service.confirm_plan(user_id=user_id, plan_id=plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{plan_id}/skip", response_model=PlanOut)
def skip_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        return service.skip_plan(user_id=user_id, plan_id=plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_plan(
    plan_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    try:
        service.delete_plan(user_id=user_id, plan_id=plan_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
