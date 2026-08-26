from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
import re
from time import sleep
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.core.cache import invalidate_plans_cache
from app.core.logging import log_background_job_event
from app.repositories.currency_repo import CurrencyRepository
from app.services.bank_currency_rate_registry import (
    BANK_RATE_PROVIDERS,
    BANK_RATE_REFRESH_MINUTES,
    BANK_RATE_STALE_MINUTES,
    DEFAULT_BANK_RATE_BANKS,
    display_scale,
)
from app.services.currency_service import CurrencyService


RATE_Q = Decimal("0.000001")
_LAST_PROVIDER_ATTEMPT: dict[str, datetime] = {}
MINSK_TZ = ZoneInfo("Europe/Minsk")


@dataclass(frozen=True)
class BankCurrencyQuote:
    bank_code: str
    bank_name: str
    currency: str
    scale: int
    buy_rate: Decimal
    sell_rate: Decimal
    channel: str
    location_name: str | None
    source_url: str
    quoted_at: datetime | None


class BankCurrencyRateRefreshService:
    PRIORBANK_URL = (
        "https://www.priorbank.by/offers/services/currency-exchange"
        "?p_p_id=ExchangeRates_INSTANCE_jPgNnkSRcCLT"
        "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        "&p_p_resource_id=ajaxPriorOnlineRatesGetRates"
        "&p_p_cacheability=cacheLevelPage"
    )
    PRIORBANK_HISTORY_URL = (
        "https://www.priorbank.by/offers/services/currency-exchange"
        "?p_p_id=ExchangeRates_INSTANCE_jPgNnkSRcCLT"
        "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
        "&p_p_resource_id=ajaxPriorOnlineRatesGetRatesByDate"
        "&p_p_cacheability=cacheLevelPage"
    )
    TECHNOBANK_URL = (
        "https://tb.by/individuals/service/currency/"
        "?bxajaxid=38b8791a0501db0a1bf0ff155f1b5bdd"
    )
    BSB_URL = "https://mobile.bsb.by/api/v1/free-zone-management/exchange-rates/rates"
    SBER_URL = "https://developer.sber-bank.by/api/rates/v1/currencyExchange"
    ISO_NUMERIC_TO_CODE = {
        156: "CNY",
        643: "RUB",
        840: "USD",
        933: "BYN",
        978: "EUR",
        985: "PLN",
    }
    ISO_CODE_TO_NUMERIC = {currency: numeric for numeric, currency in ISO_NUMERIC_TO_CODE.items()}
    TECHNOBANK_MONTHS = {
        "января": 1,
        "февраля": 2,
        "марта": 3,
        "апреля": 4,
        "мая": 5,
        "июня": 6,
        "июля": 7,
        "августа": 8,
        "сентября": 9,
        "октября": 10,
        "ноября": 11,
        "декабря": 12,
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.currency_service = CurrencyService(db)

    def refresh_due_selected_rates(self) -> list[dict]:
        refreshed: list[dict] = []
        for preference in self.repo.list_currency_preferences():
            refreshed.extend(
                self.refresh_user_selected_rates(
                    user_id=int(preference.user_id),
                    prefs=preference.data or {},
                )
            )
        return refreshed

    def refresh_user_selected_rates(
        self,
        *,
        user_id: int,
        prefs: dict | None = None,
        currencies: list[str] | None = None,
        bank_codes: list[str] | None = None,
        force: bool = False,
    ) -> list[dict]:
        config = self._resolve_config(
            user_id=user_id,
            prefs=prefs,
            currencies=currencies,
            bank_codes=bank_codes,
        )
        if not config["bank_codes"] or not config["currencies"]:
            return []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=BANK_RATE_REFRESH_MINUTES)
        latest = self.repo.get_latest_bank_rate_map()
        refreshed_rows = []
        for bank_code in config["bank_codes"]:
            provider = BANK_RATE_PROVIDERS[bank_code]
            channel = str(provider["channel"])
            provider_rows = [
                row
                for (row_bank, _currency, row_channel), row in latest.items()
                if row_bank == bank_code and row_channel == channel
            ]
            last_attempt = _LAST_PROVIDER_ATTEMPT.get(bank_code)
            available_currencies = {row.currency for row in provider_rows}
            due = force or (
                (
                    not set(config["currencies"]).issubset(available_currencies)
                    or not provider_rows
                    or max(self._aware(row.fetched_at) for row in provider_rows) < cutoff
                )
                and (last_attempt is None or last_attempt < cutoff)
            )
            if not due:
                continue
            _LAST_PROVIDER_ATTEMPT[bank_code] = now
            try:
                quotes = self._fetch_provider(bank_code)
            except Exception as exc:  # noqa: BLE001
                log_background_job_event(
                    "bank_currency_rate_refresh",
                    "provider_failed",
                    bank=bank_code,
                    error=type(exc).__name__,
                )
                continue
            for quote in quotes:
                row = self.repo.upsert_bank_rate(
                    bank_code=quote.bank_code,
                    bank_name=quote.bank_name,
                    currency=quote.currency,
                    base_currency="BYN",
                    scale=quote.scale,
                    buy_rate=quote.buy_rate,
                    sell_rate=quote.sell_rate,
                    channel=quote.channel,
                    location_name=quote.location_name,
                    source_url=quote.source_url,
                    quoted_at=quote.quoted_at,
                    fetched_at=now,
                )
                self.repo.upsert_bank_rate_snapshot(
                    bank_code=quote.bank_code,
                    bank_name=quote.bank_name,
                    currency=quote.currency,
                    base_currency="BYN",
                    rate_date=self._quote_date(quote=quote, fetched_at=now),
                    scale=quote.scale,
                    buy_rate=quote.buy_rate,
                    sell_rate=quote.sell_rate,
                    channel=quote.channel,
                    location_name=quote.location_name,
                    source_url=quote.source_url,
                    quoted_at=quote.quoted_at,
                    fetched_at=now,
                )
                refreshed_rows.append(row)
        if refreshed_rows:
            self.db.commit()
            log_background_job_event(
                "bank_currency_rate_refresh",
                "rates_refreshed",
                user_id=user_id,
                refreshed_count=len(refreshed_rows),
                banks=sorted({row.bank_code for row in refreshed_rows}),
            )
        # Bank quotes are global. Another user's refresh may have updated the
        # same provider earlier in this batch, so invalidate this user's
        # dynamic plan projection even when no fetch was needed here.
        invalidate_plans_cache(user_id)
        return [self._serialize(row, now=now) for row in refreshed_rows]

    def list_user_rates(
        self,
        *,
        user_id: int,
        prefs: dict | None = None,
        currencies: list[str] | None = None,
    ) -> list[dict]:
        config = self._resolve_config(
            user_id=user_id,
            prefs=prefs,
            currencies=currencies,
            bank_codes=None,
        )
        if not config["bank_codes"] or not config["currencies"]:
            return []
        rows = self.repo.list_bank_rates(
            bank_codes=config["bank_codes"],
            currencies=config["currencies"],
        )
        bank_order = {code: index for index, code in enumerate(config["bank_codes"])}
        currency_order = {code: index for index, code in enumerate(config["currencies"])}
        rows.sort(
            key=lambda row: (
                currency_order.get(row.currency, 999),
                bank_order.get(row.bank_code, 999),
            )
        )
        now = datetime.now(timezone.utc)
        return [self._serialize(row, now=now) for row in rows]

    def get_user_rate_history(
        self,
        *,
        user_id: int,
        currency: str,
        bank_codes: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 365,
    ) -> list[dict]:
        normalized_currency = self.currency_service._normalize_currency(currency)
        if normalized_currency == "BYN":
            raise ValueError("Bank rate history is available only for foreign currencies")
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValueError("date_from must be on or before date_to")

        currency_preferences = self.currency_service.get_currency_preferences(user_id)
        allowed_codes = [
            str(code).strip().lower()
            for code in currency_preferences.get("bank_rate_banks") or []
            if str(code).strip().lower() in BANK_RATE_PROVIDERS
        ]
        selected_codes = allowed_codes
        if bank_codes is not None:
            requested_codes = []
            for item in bank_codes:
                code = str(item or "").strip().lower()
                if not code:
                    continue
                if code not in BANK_RATE_PROVIDERS:
                    raise ValueError(f"Unsupported bank code: {code}")
                if code not in requested_codes:
                    requested_codes.append(code)
            selected_codes = [code for code in requested_codes if code in allowed_codes]
        if not selected_codes:
            return []

        rows = self.repo.list_bank_rate_history(
            bank_codes=selected_codes,
            currency=normalized_currency,
            date_from=date_from,
            date_to=date_to,
        )
        if limit > 0:
            latest_dates = sorted({row.rate_date for row in rows}, reverse=True)[:limit]
            included_dates = set(latest_dates)
            rows = [row for row in rows if row.rate_date in included_dates]
        bank_order = {code: index for index, code in enumerate(selected_codes)}
        rows.sort(key=lambda row: (row.rate_date, bank_order.get(row.bank_code, 999), row.channel, row.id))
        result = []
        for row in rows:
            provider = BANK_RATE_PROVIDERS.get(row.bank_code, {})
            result.append(
                {
                    "bank_code": row.bank_code,
                    "bank_name": row.bank_name,
                    "currency": row.currency,
                    "base_currency": row.base_currency,
                    "rate_date": row.rate_date,
                    "scale": int(row.scale or 1),
                    "buy_rate": Decimal(row.buy_rate).quantize(RATE_Q),
                    "sell_rate": Decimal(row.sell_rate).quantize(RATE_Q),
                    "channel": row.channel,
                    "channel_label": str(provider.get("channel_label") or row.channel),
                    "quoted_at": row.quoted_at,
                    "fetched_at": row.fetched_at,
                }
            )
        return result

    def _resolve_config(
        self,
        *,
        user_id: int,
        prefs: dict | None,
        currencies: list[str] | None,
        bank_codes: list[str] | None,
    ) -> dict:
        currency_config = self.currency_service.get_currency_preferences(user_id)
        active_plan_requirements = self.repo.list_active_plan_bank_requirements(user_id=user_id)
        raw_currency = prefs.get("currency") if prefs and isinstance(prefs.get("currency"), dict) else {}
        raw_banks = (
            bank_codes
            if bank_codes is not None
            else raw_currency.get("bank_rate_banks", currency_config.get("bank_rate_banks"))
        )
        if not isinstance(raw_banks, list):
            raw_banks = list(DEFAULT_BANK_RATE_BANKS)
        elif bank_codes is None:
            raw_banks = [*raw_banks, *(code for code, _currency in active_plan_requirements)]
        bank_codes = []
        for item in raw_banks:
            code = str(item or "").strip().lower()
            if code in BANK_RATE_PROVIDERS and code not in bank_codes:
                bank_codes.append(code)
        target_currencies = list(currencies or currency_config.get("tracked_currencies") or [])
        if currencies is None:
            target_currencies.extend(currency for _code, currency in active_plan_requirements)
        normalized_currencies = []
        for item in target_currencies:
            try:
                code = self.currency_service._normalize_currency(str(item))
            except ValueError:
                continue
            if code != "BYN" and code not in normalized_currencies:
                normalized_currencies.append(code)
        return {
            "bank_codes": bank_codes,
            "currencies": normalized_currencies,
        }

    def _fetch_provider(self, bank_code: str) -> list[BankCurrencyQuote]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru",
            "User-Agent": "FinancialAssistant/1.0 (+bank currency rates)",
        }
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
            if bank_code == "priorbank":
                response = client.get(self.PRIORBANK_URL)
                response.raise_for_status()
                return self._parse_priorbank(response.json())
            if bank_code == "technobank":
                response = client.get(self.TECHNOBANK_URL)
                response.raise_for_status()
                return self._parse_technobank(response.json())
            if bank_code == "bsb":
                response = client.post(
                    self.BSB_URL,
                    json={
                        "type": "CASH",
                        "bankDepartmentId": 7,
                        "period": int(datetime.now(timezone.utc).timestamp() * 1000),
                    },
                )
                response.raise_for_status()
                return self._parse_bsb(response.json())
            if bank_code == "sber":
                response = client.get(self.SBER_URL, params={"exchangeType": "Cash"})
                response.raise_for_status()
                return self._parse_sber(response.json())
        raise ValueError(f"Unsupported bank provider: {bank_code}")

    def fetch_historical_quotes_for_day(
        self,
        *,
        client: httpx.Client,
        bank_code: str,
        target_date: date,
        currencies: list[str],
    ) -> tuple[list[BankCurrencyQuote], list[str]]:
        """Fetch one provider-day without inventing synthetic calendar points.

        Priorbank exposes one archive request per currency.  Its response may
        also contain the preceding quote, so only the latest quote whose own
        timestamp belongs to ``target_date`` is accepted.  BSB exposes all
        currencies in one request and may return the last working-day quote on
        a weekend; that quote keeps its provider timestamp/date and is therefore
        safely deduplicated by the snapshot unique key.
        """

        normalized_currencies = [
            code
            for code in dict.fromkeys(str(item or "").strip().upper() for item in currencies)
            if code and code != "BYN"
        ]
        if bank_code == "priorbank":
            quotes: list[BankCurrencyQuote] = []
            errors: list[str] = []
            for currency in normalized_currencies:
                numeric = self.ISO_CODE_TO_NUMERIC.get(currency)
                if numeric is None:
                    errors.append(f"{currency}: unsupported currency")
                    continue
                try:
                    history_url = httpx.URL(self.PRIORBANK_HISTORY_URL).copy_merge_params(
                        {
                            "_ExchangeRates_INSTANCE_jPgNnkSRcCLT_currencyCode": numeric,
                            "_ExchangeRates_INSTANCE_jPgNnkSRcCLT_date": target_date.strftime("%d.%m.%Y"),
                        }
                    )
                    payload = self._request_json_with_retries(
                        client,
                        "GET",
                        history_url,
                    )
                    candidates = [
                        replace(item, source_url=self.PRIORBANK_HISTORY_URL)
                        for item in self._parse_priorbank(payload)
                        if item.currency == currency
                        and item.quoted_at is not None
                        and self._quote_date(quote=item, fetched_at=item.quoted_at) == target_date
                    ]
                    if candidates:
                        quotes.append(
                            max(
                                candidates,
                                key=lambda item: self._aware(item.quoted_at),
                            )
                        )
                except Exception as exc:  # noqa: BLE001 - one currency must not abort the archive
                    errors.append(f"{currency}: {type(exc).__name__}")
            return quotes, errors

        if bank_code == "bsb":
            end_of_day = datetime.combine(
                target_date,
                datetime.max.time().replace(microsecond=0),
                tzinfo=MINSK_TZ,
            )
            try:
                payload = self._request_json_with_retries(
                    client,
                    "POST",
                    self.BSB_URL,
                    json={
                        "type": "CASH",
                        "bankDepartmentId": 7,
                        "period": int(end_of_day.timestamp() * 1000),
                    },
                )
                quotes = []
                for item in self._parse_bsb(payload):
                    if item.currency not in normalized_currencies or item.quoted_at is None:
                        continue
                    quote_date = self._quote_date(quote=item, fetched_at=item.quoted_at)
                    if quote_date > target_date:
                        continue
                    quotes.append(replace(item, source_url=self.BSB_URL))
                return quotes, []
            except Exception as exc:  # noqa: BLE001 - caller persists provider-level progress
                return [], [type(exc).__name__]

        raise ValueError(f"Historical archive is unavailable for bank: {bank_code}")

    @staticmethod
    def _request_json_with_retries(
        client: httpx.Client,
        method: str,
        url: str | httpx.URL,
        *,
        attempts: int = 3,
        **kwargs,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                response = client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < max(1, attempts):
                    sleep(0.25 * (2**attempt))
        if last_error is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Bank history request failed")
        raise last_error

    @classmethod
    def _parse_priorbank(cls, payload: dict) -> list[BankCurrencyQuote]:
        raw = payload.get("resultEBank")
        if raw is None:
            raw = payload.get("resultByDateAndCurrencyEBank")
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        rows = data.get("simpleCurrencyList") if isinstance(data, dict) else []
        quotes = []
        for row in rows or []:
            if int(row.get("ratedCurrency") or 0) != 933:
                continue
            currency = cls.ISO_NUMERIC_TO_CODE.get(int(row.get("baseCurrency") or 0))
            if not currency:
                continue
            quoted_at = cls._parse_priorbank_datetime(
                row.get("validFromDate"),
                row.get("validFromTime"),
            )
            quotes.append(
                cls._quote(
                    bank_code="priorbank",
                    currency=currency,
                    scale=int(row.get("baseCurrencyNominal") or display_scale(currency)),
                    buy_rate=row.get("buyRate"),
                    sell_rate=row.get("sellRate"),
                    location_name="Prior Online",
                    source_url=cls.PRIORBANK_URL,
                    quoted_at=quoted_at,
                )
            )
        return quotes

    @classmethod
    def _parse_technobank(cls, payload: dict) -> list[BankCurrencyQuote]:
        encoded = str(payload.get("encoded") or "")
        if not encoded:
            raise ValueError("Technobank payload has no encoded data")
        data = json.loads(base64.b64decode(encoded).decode("utf-8"))
        items = data.get("items") if isinstance(data, dict) else []
        department = next(
            (
                item
                for item in items or []
                if str(item.get("cityId") or "") == "37" and item.get("exchangeRates")
            ),
            None,
        )
        if not department:
            department = next((item for item in items or [] if item.get("exchangeRates")), None)
        if not department:
            return []
        quoted_at = None
        for record in cls._walk_dicts(data):
            quoted_at = cls._parse_technobank_datetime(record.get("subtitle"))
            if quoted_at is not None:
                break
        location = " · ".join(
            value
            for value in (
                str(department.get("title") or "").strip(),
                str(department.get("address") or "").strip(),
            )
            if value
        )
        quotes = []
        for row in department.get("exchangeRates") or []:
            currency = str(row.get("currency") or "").strip().upper()
            quotes.append(
                cls._quote(
                    bank_code="technobank",
                    currency=currency,
                    scale=int(row.get("quantity") or display_scale(currency)),
                    buy_rate=(row.get("buying") or {}).get("value"),
                    sell_rate=(row.get("sale") or {}).get("value"),
                    location_name=location or None,
                    source_url=cls.TECHNOBANK_URL,
                    quoted_at=quoted_at,
                )
            )
        return quotes

    @classmethod
    def _parse_bsb(cls, payload: dict) -> list[BankCurrencyQuote]:
        quoted_at = cls._datetime_from_millis(payload.get("fromTime"))
        quotes = []
        for row in payload.get("rates") or []:
            if str(row.get("sellCurrencyName") or "").upper() != "BYN":
                continue
            currency = str(row.get("buyCurrencyName") or "").strip().upper()
            quotes.append(
                cls._quote(
                    bank_code="bsb",
                    currency=currency,
                    scale=int(row.get("buyCurrencyScale") or display_scale(currency)),
                    buy_rate=row.get("scaledBuyAmount"),
                    sell_rate=row.get("scaledSellAmount"),
                    location_name="Отделение №7",
                    source_url=cls.BSB_URL,
                    quoted_at=quoted_at,
                )
            )
        return quotes

    @classmethod
    def _parse_sber(cls, payload: Any) -> list[BankCurrencyQuote]:
        grouped: dict[str, dict[str, list[tuple[Decimal, dict]]]] = {}
        for row in cls._walk_dicts(payload):
            rate_value = row.get("exchangeRate")
            direction = str(row.get("direction") or "").strip().lower()
            source = str(row.get("sourceCurrency") or "").strip().upper()
            target = str(row.get("targetCurrency") or "").strip().upper()
            if rate_value in (None, "") or direction not in {"buy", "sell"}:
                continue
            if target == "BYN" and source and source != "BYN":
                currency = source
            else:
                continue
            try:
                rate = Decimal(str(rate_value))
            except Exception:  # noqa: BLE001
                continue
            if rate <= 0:
                continue
            grouped.setdefault(currency, {"buy": [], "sell": []})[direction].append((rate, row))
        quotes = []
        for currency, directions in grouped.items():
            if not directions["buy"] or not directions["sell"]:
                continue
            buy_rate, buy_row = max(directions["buy"], key=lambda item: item[0])
            sell_rate, sell_row = min(directions["sell"], key=lambda item: item[0])
            scale = int(buy_row.get("scaleCurrency") or sell_row.get("scaleCurrency") or display_scale(currency))
            location = str(
                buy_row.get("branchName")
                or buy_row.get("idBranch")
                or sell_row.get("branchName")
                or sell_row.get("idBranch")
                or "Лучший наличный курс"
            )
            quoted_at = cls._parse_iso_datetime(
                buy_row.get("updatedDateTime")
                or buy_row.get("updateDateTime")
                or buy_row.get("dateTime")
            )
            quotes.append(
                cls._quote(
                    bank_code="sber",
                    currency=currency,
                    scale=scale,
                    buy_rate=buy_rate,
                    sell_rate=sell_rate,
                    location_name=location,
                    source_url=cls.SBER_URL,
                    quoted_at=quoted_at,
                )
            )
        return quotes

    @staticmethod
    def _walk_dicts(value: Any):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from BankCurrencyRateRefreshService._walk_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from BankCurrencyRateRefreshService._walk_dicts(child)

    @classmethod
    def _quote(
        cls,
        *,
        bank_code: str,
        currency: str,
        scale: int,
        buy_rate,
        sell_rate,
        location_name: str | None,
        source_url: str,
        quoted_at: datetime | None,
    ) -> BankCurrencyQuote:
        normalized_currency = str(currency or "").strip().upper()
        source_scale = int(scale or 0)
        buy = Decimal(str(buy_rate))
        sell = Decimal(str(sell_rate))
        if len(normalized_currency) != 3 or buy <= 0 or sell <= 0 or source_scale <= 0:
            raise ValueError(f"Invalid {bank_code} bank quote")
        target_scale = display_scale(normalized_currency)
        buy = (buy / source_scale * target_scale).quantize(RATE_Q)
        sell = (sell / source_scale * target_scale).quantize(RATE_Q)
        provider = BANK_RATE_PROVIDERS[bank_code]
        return BankCurrencyQuote(
            bank_code=bank_code,
            bank_name=str(provider["name"]),
            currency=normalized_currency,
            scale=target_scale,
            buy_rate=buy,
            sell_rate=sell,
            channel=str(provider["channel"]),
            location_name=location_name,
            source_url=source_url,
            quoted_at=quoted_at,
        )

    @staticmethod
    def _parse_priorbank_datetime(date_value, time_value) -> datetime | None:
        try:
            parsed = datetime.strptime(
                f"{str(date_value).strip()} {str(time_value).strip()}",
                "%d.%m.%Y %H:%M",
            )
            return parsed.replace(tzinfo=ZoneInfo("Europe/Minsk"))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse_technobank_datetime(cls, value) -> datetime | None:
        raw = str(value or "").strip().lower().replace("ё", "е")
        match = re.search(
            r"(?P<day>\d{1,2})\s+(?P<month>[а-я]+)\s+(?P<year>\d{4})"
            r"(?:\s*г?\.?\s*[,·]?\s*(?:в\s+)?)"
            r"(?P<hour>\d{1,2}):(?P<minute>\d{2})",
            raw,
        )
        if not match:
            return None
        month = cls.TECHNOBANK_MONTHS.get(match.group("month"))
        if month is None:
            return None
        try:
            return datetime(
                int(match.group("year")),
                month,
                int(match.group("day")),
                int(match.group("hour")),
                int(match.group("minute")),
                tzinfo=MINSK_TZ,
            )
        except ValueError:
            return None

    @staticmethod
    def _parse_iso_datetime(value) -> datetime | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo("Europe/Minsk"))
        except ValueError:
            return None

    @staticmethod
    def _datetime_from_millis(value) -> datetime | None:
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @classmethod
    def _quote_date(cls, *, quote: BankCurrencyQuote, fetched_at: datetime) -> date:
        observed_at = quote.quoted_at or fetched_at
        return cls._aware(observed_at).astimezone(MINSK_TZ).date()

    @classmethod
    def _serialize(cls, row, *, now: datetime) -> dict:
        fetched_at = cls._aware(row.fetched_at)
        quoted_at = cls._aware(row.quoted_at) if row.quoted_at else None
        freshness_timestamp = min(
            value for value in (fetched_at, quoted_at) if value is not None
        )
        stale = freshness_timestamp < now - timedelta(minutes=BANK_RATE_STALE_MINUTES)
        provider = BANK_RATE_PROVIDERS.get(row.bank_code, {})
        return {
            "bank_code": row.bank_code,
            "bank_name": row.bank_name,
            "currency": row.currency,
            "base_currency": row.base_currency,
            "scale": int(row.scale or 1),
            "buy_rate": Decimal(row.buy_rate).quantize(RATE_Q),
            "sell_rate": Decimal(row.sell_rate).quantize(RATE_Q),
            "channel": row.channel,
            "channel_label": str(provider.get("channel_label") or row.channel),
            "location_name": row.location_name,
            "quoted_at": row.quoted_at,
            "fetched_at": row.fetched_at,
            "stale": stale,
        }
