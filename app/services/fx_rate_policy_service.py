from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.currency_repo import CurrencyRepository
from app.services.bank_currency_rate_registry import (
    BANK_RATE_PROVIDERS,
    BANK_RATE_STALE_MINUTES,
    display_scale,
)


RATE_Q = Decimal("0.000001")
FX_RATE_SOURCES = frozenset({"nbrb", "bank", "manual"})
FX_RATE_KINDS = frozenset({"buy", "sell"})
FX_PAYMENT_MODES = frozenset({"valuation", "direct_conversion", "foreign_balance"})


@dataclass(frozen=True)
class FxRateResolution:
    rate: Decimal
    display_rate: Decimal
    scale: int
    source: str
    bank_code: str | None = None
    bank_name: str | None = None
    bank_channel: str | None = None
    rate_kind: str | None = None
    quoted_at: datetime | None = None
    fetched_at: datetime | None = None
    rate_date: date | None = None
    stale: bool = False

    def operation_snapshot(self, *, payment_mode: str) -> dict:
        return {
            "fx_rate": self.rate,
            "fx_rate_source": self.source,
            "fx_bank_code": self.bank_code,
            "fx_bank_name": self.bank_name,
            "fx_bank_channel": self.bank_channel,
            "fx_rate_kind": self.rate_kind,
            "fx_rate_scale": self.scale,
            "fx_rate_date": self.rate_date,
            "fx_quoted_at": self.quoted_at,
            "fx_fetched_at": self.fetched_at,
            "fx_rate_stale": self.stale,
            "fx_payment_mode": payment_mode,
        }


class FxRatePolicyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)

    @staticmethod
    def normalize_source(value: str | None, *, default: str | None = None) -> str | None:
        normalized = str(value or default or "").strip().lower() or None
        if normalized is not None and normalized not in FX_RATE_SOURCES:
            raise ValueError("fx_rate_source must be one of: nbrb, bank, manual")
        return normalized

    @staticmethod
    def normalize_rate_kind(value: str | None) -> str | None:
        normalized = str(value or "").strip().lower() or None
        if normalized is not None and normalized not in FX_RATE_KINDS:
            raise ValueError("fx_rate_kind must be one of: buy, sell")
        return normalized

    @staticmethod
    def normalize_payment_mode(value: str | None, *, default: str = "valuation") -> str:
        normalized = str(value or default).strip().lower()
        if normalized not in FX_PAYMENT_MODES:
            raise ValueError(
                "fx_payment_mode must be one of: valuation, direct_conversion, foreign_balance"
            )
        return normalized

    @staticmethod
    def normalize_bank_code(value: str | None) -> str | None:
        normalized = str(value or "").strip().lower() or None
        if normalized is not None and normalized not in BANK_RATE_PROVIDERS:
            raise ValueError("Unsupported fx_bank_code")
        return normalized

    @staticmethod
    def normalize_bank_channel(*, bank_code: str | None, value: str | None) -> str | None:
        normalized = str(value or "").strip().lower() or None
        if not bank_code:
            return normalized
        expected = str(BANK_RATE_PROVIDERS[bank_code]["channel"])
        if normalized is not None and normalized != expected:
            raise ValueError(f"Bank {bank_code} does not provide the {normalized} rate channel")
        return normalized or expected

    @classmethod
    def validate_payment_mode(cls, *, kind: str, currency: str, base_currency: str, payment_mode: str) -> None:
        if payment_mode in {"direct_conversion", "foreign_balance"}:
            if kind != "expense":
                raise ValueError(f"fx_payment_mode {payment_mode} is supported only for expense operations")
            if currency == base_currency:
                raise ValueError(f"fx_payment_mode {payment_mode} requires a foreign currency")

    def resolve(
        self,
        *,
        user_id: int,
        currency: str,
        base_currency: str,
        source: str,
        bank_code: str | None = None,
        bank_channel: str | None = None,
        rate_kind: str | None = None,
        manual_rate: Decimal | None = None,
        legacy_unit_rate: Decimal | None = None,
        as_of: date | None = None,
    ) -> FxRateResolution:
        normalized_source = self.normalize_source(source)
        if normalized_source is None:
            raise ValueError("fx_rate_source is required")
        normalized_currency = str(currency or "").strip().upper()
        normalized_base = str(base_currency or "").strip().upper()
        if normalized_currency == normalized_base:
            return FxRateResolution(
                rate=Decimal("1.000000"),
                display_rate=Decimal("1.000000"),
                scale=1,
                source=normalized_source,
            )
        if normalized_source == "nbrb":
            row = (
                self.repo.get_nbrb_rate_as_of(
                    user_id=user_id,
                    currency=normalized_currency,
                    rate_date=as_of,
                )
                if as_of is not None
                else self.repo.get_latest_nbrb_rate_map(user_id=user_id).get(normalized_currency)
            )
            if row is None:
                qualifier = f" на {as_of.isoformat()}" if as_of is not None else ""
                raise ValueError(f"Нет курса НБРБ для {normalized_currency}{qualifier}")
            unit_rate = self._rate(row.rate)
            if unit_rate <= 0:
                raise ValueError(f"Некорректный курс НБРБ для {normalized_currency}")
            scale = display_scale(normalized_currency)
            return FxRateResolution(
                rate=unit_rate,
                display_rate=self._rate(unit_rate * scale),
                scale=scale,
                source="nbrb",
                fetched_at=self._aware(getattr(row, "created_at", None)),
                rate_date=row.rate_date,
            )
        if normalized_source == "bank":
            normalized_bank = self.normalize_bank_code(bank_code)
            if normalized_bank is None:
                raise ValueError("fx_bank_code is required for bank rate source")
            normalized_channel = self.normalize_bank_channel(
                bank_code=normalized_bank,
                value=bank_channel,
            )
            normalized_kind = self.normalize_rate_kind(rate_kind)
            if normalized_kind is None:
                raise ValueError("fx_rate_kind is required for bank rate source")
            row = self.repo.get_bank_rate(
                bank_code=normalized_bank,
                currency=normalized_currency,
                base_currency=normalized_base,
                channel=str(normalized_channel),
            )
            if row is None:
                raise ValueError(
                    f"Нет курса {normalized_currency}/{normalized_base} для банка {normalized_bank} "
                    f"({normalized_channel})"
                )
            scale = max(1, int(row.scale or 1))
            display_rate_value = row.buy_rate if normalized_kind == "buy" else row.sell_rate
            resolved_display_rate = self._rate(display_rate_value)
            unit_rate = self._rate(resolved_display_rate / Decimal(scale))
            if unit_rate <= 0:
                raise ValueError(f"Некорректный курс банка для {normalized_currency}")
            fetched_at = self._aware(row.fetched_at)
            quoted_at = self._aware(row.quoted_at)
            stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=BANK_RATE_STALE_MINUTES)
            freshness_timestamp = min(
                value for value in (fetched_at, quoted_at) if value is not None
            ) if fetched_at or quoted_at else None
            return FxRateResolution(
                rate=unit_rate,
                display_rate=resolved_display_rate,
                scale=scale,
                source="bank",
                bank_code=row.bank_code,
                bank_name=row.bank_name,
                bank_channel=row.channel,
                rate_kind=normalized_kind,
                quoted_at=quoted_at,
                fetched_at=fetched_at,
                rate_date=(quoted_at or fetched_at).date() if (quoted_at or fetched_at) else None,
                stale=freshness_timestamp is None or freshness_timestamp < stale_cutoff,
            )
        scale = display_scale(normalized_currency)
        if manual_rate is not None:
            resolved_display_rate = self._rate(manual_rate)
            unit_rate = self._rate(resolved_display_rate / Decimal(scale))
        else:
            # Legacy ``fx_rate`` has always meant a per-one-unit rate.  It must
            # not be divided by the RUB display scale a second time.
            unit_rate = self._rate(legacy_unit_rate)
            resolved_display_rate = self._rate(unit_rate * Decimal(scale))
        if unit_rate <= 0:
            raise ValueError("fx_manual_rate must be positive for manual rate source")
        return FxRateResolution(
            rate=unit_rate,
            display_rate=resolved_display_rate,
            scale=scale,
            source="manual",
        )

    def get_rate_options(
        self,
        *,
        user_id: int,
        currency: str,
        base_currency: str,
        as_of: date | None = None,
    ) -> dict:
        normalized_currency = str(currency or "").strip().upper()
        normalized_base = str(base_currency or "").strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        if len(normalized_base) != 3 or not normalized_base.isalpha():
            raise ValueError("base_currency must be a 3-letter ISO code")
        if normalized_currency == normalized_base:
            raise ValueError("currency must differ from base_currency")
        scale = display_scale(normalized_currency)
        nbrb_row = (
            self.repo.get_nbrb_rate_as_of(
                user_id=user_id,
                currency=normalized_currency,
                rate_date=as_of,
            )
            if as_of is not None
            else self.repo.get_latest_nbrb_rate_map(user_id=user_id).get(normalized_currency)
        )
        nbrb_rate = None
        if nbrb_row is not None:
            unit_rate = self._rate(nbrb_row.rate)
            nbrb_rate = {
                "rate": self._rate(unit_rate * Decimal(scale)),
                "unit_rate": unit_rate,
                "scale": scale,
                "rate_date": nbrb_row.rate_date,
                "source": nbrb_row.source,
            }
        rows = [
            row
            for row in self.repo.list_bank_rates(currencies=[normalized_currency])
            if str(row.base_currency).upper() == normalized_base
            and row.bank_code in BANK_RATE_PROVIDERS
        ]
        rows_by_provider = {
            (row.bank_code, row.channel): row
            for row in rows
        }
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(minutes=BANK_RATE_STALE_MINUTES)
        bank_rates = []
        providers = []
        for bank_code, provider in BANK_RATE_PROVIDERS.items():
            channel = str(provider["channel"])
            row = rows_by_provider.get((bank_code, channel))
            providers.append(
                {
                    "bank_code": bank_code,
                    "bank_name": str(provider["name"]),
                    "channel": channel,
                    "channel_label": str(provider.get("channel_label") or channel),
                    "has_quote": row is not None,
                }
            )
            if row is None:
                continue
            row_scale = max(1, int(row.scale or 1))
            fetched_at = self._aware(row.fetched_at)
            quoted_at = self._aware(row.quoted_at)
            freshness_timestamp = min(
                value for value in (fetched_at, quoted_at) if value is not None
            ) if fetched_at or quoted_at else None
            bank_rates.append(
                {
                    "bank_code": row.bank_code,
                    "bank_name": row.bank_name,
                    "currency": row.currency,
                    "base_currency": row.base_currency,
                    "scale": row_scale,
                    "buy_rate": self._rate(row.buy_rate),
                    "sell_rate": self._rate(row.sell_rate),
                    "buy_unit_rate": self._rate(Decimal(row.buy_rate) / Decimal(row_scale)),
                    "sell_unit_rate": self._rate(Decimal(row.sell_rate) / Decimal(row_scale)),
                    "channel": row.channel,
                    "channel_label": str(provider.get("channel_label") or row.channel),
                    "location_name": row.location_name,
                    "quoted_at": quoted_at,
                    "fetched_at": fetched_at,
                    "stale": freshness_timestamp is None or freshness_timestamp < stale_cutoff,
                }
            )
        return {
            "currency": normalized_currency,
            "base_currency": normalized_base,
            "display_scale": scale,
            "nbrb_rate": nbrb_rate,
            "bank_rates": bank_rates,
            "providers": providers,
        }

    @staticmethod
    def _rate(value: Decimal | None) -> Decimal:
        return Decimal(value or 0).quantize(RATE_Q)

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
