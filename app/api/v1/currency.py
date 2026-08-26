from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.currency import (
    CurrencyAvailableBalanceOut,
    CurrencyBankRateHistoryPointOut,
    CurrencyOverviewOut,
    CurrencyPerformanceHistoryOut,
    CurrencyRateHistoryPointOut,
    CurrencyRateOut,
    CurrencyRateOptionsOut,
    CurrencyTradeListOut,
    CurrencyRateUpsert,
    CurrencyTradeCreate,
    CurrencyTradeOut,
    CurrencyTradeUpdate,
)
from app.services.currency_rate_refresh_service import CurrencyRateRefreshService
from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService
from app.services.currency_service import CurrencyService
from app.services.fx_rate_policy_service import FxRatePolicyService
from app.services.bank_currency_rate_registry import BANK_RATE_PROVIDERS

router = APIRouter(prefix="/currency", tags=["currency"])


@router.get("/available-balance", response_model=CurrencyAvailableBalanceOut)
def get_currency_available_balance(
    currency: str = Query(min_length=3, max_length=3),
    as_of: date = Query(),
    exclude_linked_operation_id: int | None = Query(default=None, ge=1),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CurrencyService(db)
    try:
        return service.get_available_balance(
            user_id=user_id,
            currency=currency,
            as_of=as_of,
            exclude_linked_operation_id=exclude_linked_operation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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


@router.get("/rate-options", response_model=CurrencyRateOptionsOut)
def get_currency_rate_options(
    currency: str = Query(min_length=3, max_length=3),
    base_currency: str = Query(default="BYN", min_length=3, max_length=3),
    as_of: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        return FxRatePolicyService(db).get_rate_options(
            user_id=user_id,
            currency=currency,
            base_currency=base_currency,
            as_of=as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/rate-options/refresh", response_model=CurrencyRateOptionsOut)
def refresh_currency_rate_options(
    currency: str = Query(min_length=3, max_length=3),
    base_currency: str = Query(default="BYN", min_length=3, max_length=3),
    bank_code: str | None = Query(default=None, max_length=32),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    policy = FxRatePolicyService(db)
    try:
        normalized_bank = policy.normalize_bank_code(bank_code)
        refreshed = BankCurrencyRateRefreshService(db).refresh_user_selected_rates(
            user_id=user_id,
            currencies=[currency],
            bank_codes=[normalized_bank] if normalized_bank else list(BANK_RATE_PROVIDERS),
            force=True,
        )
        normalized_currency = currency.strip().upper()
        refreshed_pairs = {
            (str(item.get("bank_code") or "").lower(), str(item.get("currency") or "").upper())
            for item in refreshed
        }
        if normalized_bank and (normalized_bank, normalized_currency) not in refreshed_pairs:
            raise RuntimeError(f"Не удалось обновить курс {normalized_bank} для {normalized_currency}")
        if not normalized_bank and not any(pair[1] == normalized_currency for pair in refreshed_pairs):
            raise RuntimeError(f"Не удалось обновить банковские курсы для {normalized_currency}")
        return policy.get_rate_options(
            user_id=user_id,
            currency=currency,
            base_currency=base_currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


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
    limit: int = Query(default=120, ge=1, le=3660),
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


@router.get("/bank-rates/history", response_model=list[CurrencyBankRateHistoryPointOut])
def get_bank_currency_rate_history(
    currency: str = Query(min_length=3, max_length=3),
    bank_code: list[str] | None = Query(default=None),
    bank_codes: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=365, ge=1, le=3660),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    selected_codes = list(bank_code or [])
    if bank_codes:
        selected_codes.extend(item.strip() for item in bank_codes.split(","))
    try:
        return BankCurrencyRateRefreshService(db).get_user_rate_history(
            user_id=user_id,
            currency=currency,
            bank_codes=selected_codes or None,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
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
        refreshed = service.refresh_user_tracked_rates(
            user_id=user_id,
            currencies=[currency] if currency else None,
            force=True,
        )
        BankCurrencyRateRefreshService(db).refresh_user_selected_rates(
            user_id=user_id,
            currencies=[currency] if currency else None,
            force=True,
        )
        return refreshed
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
