from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.work import (
    EmploymentContractIn,
    EmploymentContractOut,
    WorkDayOut,
    WorkDayOverrideIn,
    WorkDayRangeOverrideIn,
    WorkMonthOut,
    WorkPaymentCandidateListOut,
    WorkPaymentHistoryOut,
    WorkPaymentHistoryItemOut,
    WorkPaymentLinkIn,
    WorkProfileOut,
    WorkProfileUpdate,
    WorkStatisticsOut,
    WorkCompanyOut,
)
from app.services.work_service import WorkService


router = APIRouter(prefix="/work", tags=["work"])


@router.get("/profile", response_model=WorkProfileOut)
def get_work_profile(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return WorkService(db).get_profile(user_id=user_id)


@router.put("/profile", response_model=WorkProfileOut)
def update_work_profile(
    payload: WorkProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).update_profile(user_id=user_id, payload=payload.model_dump())
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/month", response_model=WorkMonthOut)
def get_work_month(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).get_month(user_id=user_id, year=year, month=month)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/payments/history", response_model=WorkPaymentHistoryOut)
def get_work_payment_history(
    date_from: date = Query(),
    date_to: date = Query(),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).list_payment_history(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/payments/candidates", response_model=WorkPaymentCandidateListOut)
def get_work_payment_candidates(
    date_from: date = Query(),
    date_to: date = Query(),
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).list_payment_candidates(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            q=q,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/payments/links",
    response_model=WorkPaymentHistoryItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_work_payment_link(
    payload: WorkPaymentLinkIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).create_payment_link(
            user_id=user_id,
            operation_id=payload.operation_id,
            role=payload.role,
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete(
    "/payments/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_work_payment_link(
    link_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        WorkService(db).delete_payment_link(user_id=user_id, link_id=link_id)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/statistics", response_model=WorkStatisticsOut)
def get_work_statistics(
    period: str = Query(default="month", pattern="^(month|year|all_time|custom)$"),
    anchor: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).get_statistics(
            user_id=user_id,
            period=period,
            anchor=anchor,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/days/{work_date}", response_model=WorkDayOut)
def upsert_work_day(
    work_date: date,
    payload: WorkDayOverrideIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return WorkService(db).upsert_override(user_id=user_id, work_date=work_date, payload=payload.model_dump())


@router.put("/days")
def upsert_work_day_range(
    payload: WorkDayRangeOverrideIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    values = payload.model_dump(exclude={"date_from", "date_to"})
    count = WorkService(db).upsert_override_range(
        user_id=user_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
        payload=values,
    )
    return {"updated": count}


@router.delete("/days/{work_date}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def reset_work_day(
    work_date: date,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        WorkService(db).delete_override(user_id=user_id, work_date=work_date)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/contracts", response_model=list[EmploymentContractOut])
def list_contracts(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return WorkService(db).list_contracts(user_id=user_id)


@router.get("/companies", response_model=list[WorkCompanyOut])
def list_companies(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return WorkService(db).list_companies(user_id=user_id)


@router.post("/contracts", response_model=EmploymentContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(
    payload: EmploymentContractIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).create_contract(user_id=user_id, payload=payload.model_dump())
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/contracts/{contract_id}", response_model=EmploymentContractOut)
def update_contract(
    contract_id: int,
    payload: EmploymentContractIn,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return WorkService(db).update_contract(
            user_id=user_id,
            contract_id=contract_id,
            payload=payload.model_dump(),
        )
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_contract(
    contract_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        WorkService(db).delete_contract(user_id=user_id, contract_id=contract_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
