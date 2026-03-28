from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.services.currency_service import CurrencyService


class CurrencyRateRefreshService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.currency_service = CurrencyService(db)
        self.settings = get_settings()

    def refresh_due_tracked_rates(self) -> list[dict]:
        refreshed: list[dict] = []
        for preference in self.repo.list_currency_preferences():
            user_id = int(preference.user_id)
            try:
                result = self.refresh_user_tracked_rates(user_id=user_id, prefs=preference.data or {})
            except Exception as exc:  # noqa: BLE001
                log_background_job_event(
                    "currency_rate_refresh",
                    "user_refresh_failed",
                    user_id=user_id,
                    error=type(exc).__name__,
                )
                continue
            if result:
                refreshed.append({"user_id": user_id, "rates": result})
        if refreshed:
            log_background_job_event(
                "currency_rate_refresh",
                "batch_completed",
                refreshed_users=len(refreshed),
                refreshed_rates=sum(len(item["rates"]) for item in refreshed),
            )
        return refreshed

    def refresh_user_tracked_rates(
        self,
        *,
        user_id: int,
        prefs: dict | None = None,
        currencies: list[str] | None = None,
        force: bool = False,
    ) -> list[dict]:
        currency_prefs = self.currency_service.get_currency_preferences(user_id)
        tracked = list(currency_prefs.get("tracked_currencies") or [])
        target_currencies = [
            self.currency_service._normalize_currency(code)
            for code in (currencies or tracked)
            if str(code or "").strip()
        ]
        if target_currencies:
            tracked = list(dict.fromkeys(target_currencies))
        if not tracked:
            return []
        timezone_name = self._resolve_timezone_name(prefs or {})
        target_date = datetime.now(ZoneInfo(timezone_name)).date()
        latest_rate_triplets = self.repo.get_latest_rate_triplet_map(user_id=user_id)
        missing = [
            currency
            for currency in tracked
            if force or not latest_rate_triplets.get(currency) or latest_rate_triplets[currency][0].rate_date < target_date
        ]
        if not missing:
            return []
        fetched = self._fetch_rates(missing)
        refreshed: list[dict] = []
        for currency in missing:
            rate_payload = fetched.get(currency)
            if rate_payload is None:
                log_background_job_event(
                    "currency_rate_refresh",
                    "currency_skipped",
                    user_id=user_id,
                    currency=currency,
                    reason="rate_not_available",
                )
                continue
            if isinstance(rate_payload, dict):
                rate = rate_payload["rate"]
                effective_date = rate_payload.get("effective_date") or target_date
                effective_date_inferred = rate_payload.get("effective_date_inferred", True)
            else:
                rate = rate_payload
                effective_date = target_date
                effective_date_inferred = True
            latest_rows = latest_rate_triplets.get(currency)
            latest_row = latest_rows[0] if latest_rows else None
            if effective_date > target_date:
                effective_date = target_date
            if (
                not force
                and latest_row
                and effective_date_inferred
                and latest_row.rate_date < target_date
                and Decimal(str(rate)) == Decimal(str(latest_row.rate))
            ):
                log_background_job_event(
                    "currency_rate_refresh",
                    "currency_skipped",
                    user_id=user_id,
                    currency=currency,
                    reason="latest_official_rate_not_published_yet",
                    latest_rate_date=latest_row.rate_date.isoformat(),
                )
                continue
            if not force and latest_row and effective_date <= latest_row.rate_date:
                continue
            refreshed.append(
                self.currency_service.upsert_rate(
                    user_id=user_id,
                    currency=currency,
                    rate=rate,
                    rate_date=effective_date,
                    source="nbrb_auto",
                )
            )
        if refreshed:
            log_background_job_event(
                "currency_rate_refresh",
                "user_refreshed",
                user_id=user_id,
                refreshed_count=len(refreshed),
                rate_date=target_date.isoformat(),
            )
        return refreshed

    def backfill_user_rate_history(
        self,
        *,
        user_id: int,
        currency: str,
        date_from: date,
        date_to: date,
        force: bool = False,
    ) -> list[dict]:
        normalized_currency = self.currency_service._normalize_currency(currency)
        if date_to < date_from:
            raise ValueError("date_to must be on or after date_from")
        total_days = (date_to - date_from).days + 1
        if total_days > 370:
            raise ValueError("Requested history window is too large")
        existing_rows = self.repo.list_rate_history(
            user_id=user_id,
            currency=normalized_currency,
            limit=370,
            date_from=date_from,
            date_to=date_to,
        )
        existing_dates = {row.rate_date for row in existing_rows}
        refreshed: list[dict] = []
        cursor = date_from
        while cursor <= date_to:
            if not force and cursor in existing_dates:
                cursor += timedelta(days=1)
                continue
            rate = self._fetch_rate_for_date(normalized_currency, cursor)
            if rate is None:
                cursor += timedelta(days=1)
                continue
            refreshed.append(
                self.currency_service.upsert_rate(
                    user_id=user_id,
                    currency=normalized_currency,
                    rate=rate,
                    rate_date=cursor,
                    source="nbrb_history",
                )
            )
            cursor += timedelta(days=1)
        return refreshed

    def _resolve_timezone_name(self, prefs: dict) -> str:
        ui_prefs = prefs.get("ui") if isinstance(prefs.get("ui"), dict) else {}
        timezone_name = str(ui_prefs.get("timezone") or "").strip()
        if not timezone_name or timezone_name == "auto":
            timezone_name = str(ui_prefs.get("browser_timezone") or "").strip()
        return timezone_name or "Europe/Minsk"

    def _fetch_rates(self, currencies: list[str]) -> dict[str, dict]:
        results: dict[str, dict] = {}
        if not currencies:
            return results
        with httpx.Client(timeout=10.0) as client:
            for currency in currencies:
                response = client.get(self._build_provider_url(currency))
                response.raise_for_status()
                payload = response.json()
                raw_rate = payload.get("Cur_OfficialRate")
                if raw_rate is None:
                    raise ValueError(f"Missing Cur_OfficialRate for {currency}")
                effective_date = self._extract_effective_date(payload)
                results[currency] = {
                    "rate": float(raw_rate),
                    "effective_date": effective_date,
                    "effective_date_inferred": effective_date is None,
                }
        return results

    def _fetch_rate_for_date(self, currency: str, rate_date: date) -> float | None:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self._build_provider_url(currency, rate_date))
            response.raise_for_status()
            payload = response.json()
            raw_rate = payload.get("Cur_OfficialRate")
            if raw_rate is None:
                return None
            return float(raw_rate)

    def _build_provider_url(self, currency: str, rate_date: date | None = None) -> str:
        base_url = self.settings.currency_rate_provider_url.format(code=currency)
        if not rate_date:
            return base_url
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}ondate={rate_date.isoformat()}"

    def _extract_effective_date(self, payload: dict) -> date | None:
        for key in ("Date", "Cur_Date", "Cur_DateStart"):
            raw = payload.get(key)
            if raw in (None, ""):
                continue
            text = str(raw).strip()
            if not text:
                continue
            normalized = text.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized).date()
            except ValueError:
                try:
                    return date.fromisoformat(text[:10])
                except ValueError:
                    continue
        return None
