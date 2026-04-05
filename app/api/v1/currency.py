from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.currency import (
    CurrencyOverviewOut,
    CurrencyPerformanceHistoryOut,
    CurrencyRateHistoryPointOut,
    CurrencyRateOut,
    CurrencyTradeListOut,
    CurrencyRateUpsert,
    CurrencyTradeCreate,
    CurrencyTradeOut,
    CurrencyTradeUpdate,
)
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService
from app.services.currency_service import CurrencyService

router = APIRouter(prefix="/currency", tags=["currency"])


@router.get("/overview", response_model=CurrencyOverviewOut)
def get_currency_overview(
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    trades_limit: int = Query(default=100, ge=1, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.get_overview(user_id=user_id, currency=currency, trades_limit=trades_limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/trades", response_model=CurrencyTradeListOut)
def list_currency_trades(
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.list_trades(user_id=user_id, currency=currency, page=page, page_size=page_size)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/performance/history", response_model=CurrencyPerformanceHistoryOut)
def get_currency_performance_history(
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.get_performance_history(
            user_id=user_id,
            currency=currency,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/trades", response_model=CurrencyTradeOut, status_code=status.HTTP_201_CREATED)
def create_currency_trade(
    payload: CurrencyTradeCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.create_trade(
            user_id=user_id,
            side=payload.side,
            asset_currency=payload.asset_currency,
            quote_currency=payload.quote_currency,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            fee=payload.fee,
            trade_kind=payload.trade_kind,
            linked_operation_id=payload.linked_operation_id,
            trade_date=payload.trade_date,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/trades/{trade_id}", response_model=CurrencyTradeOut)
def update_currency_trade(
    trade_id: int,
    payload: CurrencyTradeUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.update_trade(
            user_id=user_id,
            trade_id=trade_id,
            side=payload.side,
            asset_currency=payload.asset_currency,
            quote_currency=payload.quote_currency,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            fee=payload.fee,
            trade_kind=payload.trade_kind,
            linked_operation_id=payload.linked_operation_id,
            trade_date=payload.trade_date,
            note=payload.note,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "Currency trade not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.delete("/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_currency_trade(
    trade_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        service.delete_trade(user_id=user_id, trade_id=trade_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "Currency trade not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.put("/rates/current", response_model=CurrencyRateOut)
def upsert_currency_rate(
    payload: CurrencyRateUpsert,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.upsert_rate(
            user_id=user_id,
            currency=payload.currency,
            rate=payload.rate,
            rate_date=payload.rate_date,
            source=payload.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/rates/history", response_model=list[CurrencyRateHistoryPointOut])
def get_currency_rate_history(
    currency: str = Query(min_length=3, max_length=3),
    limit: int = Query(default=120, ge=1, le=365),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.get_rate_history(
            user_id=user_id,
            currency=currency,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/rates/refresh", response_model=list[CurrencyRateOut])
def refresh_currency_rates(
    currency: str | None = Query(default=None, min_length=3, max_length=3),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyRateRefreshService(db)
    try:
        return service.refresh_user_tracked_rates(
            user_id=user_id,
            currencies=[currency] if currency else None,
            force=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/rates/history/fill", response_model=list[CurrencyRateOut])
def fill_currency_rate_history(
    currency: str = Query(min_length=3, max_length=3),
    date_from: date = Query(),
    date_to: date = Query(),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyRateRefreshService(db)
    try:
        return service.backfill_user_rate_history(
            user_id=user_id,
            currency=currency,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
