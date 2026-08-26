from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable

from sqlalchemy.orm import Session

from app.repositories.currency_repo import NBRB_RATE_SOURCES
from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService
from app.services.bank_currency_rate_registry import display_scale
from app.services.currency_service import CurrencyService
from app.services.telegram_currency_digest_chart_renderer import (
    CurrencyDigestChartPanel,
    CurrencyDigestChartPoint,
    CurrencyDigestChartSeries,
    TelegramCurrencyDigestChartPayload,
)


class TelegramCurrencyDigestChartDataService:
    """Build a renderer-ready seven-day snapshot from the existing FX stores."""

    PERIOD_DAYS = 7
    MAX_PANELS = 4

    def __init__(self, db: Session):
        self.currency_service = CurrencyService(db)
        self.bank_rate_service = BankCurrencyRateRefreshService(db)

    def build_payload(
        self,
        *,
        user_id: int,
        tracked_currencies: Iterable[str],
        bank_codes: list[str] | None,
        overview: dict,
        as_of: date,
    ) -> TelegramCurrencyDigestChartPayload:
        date_from = as_of - timedelta(days=self.PERIOD_DAYS - 1)
        positions = {
            str(item.get("currency") or "").upper(): item
            for item in overview.get("positions") or []
        }
        base_currency = str(overview.get("base_currency") or "BYN").upper()
        panels = []
        seen = set()
        for raw_currency in tracked_currencies:
            if len(panels) >= self.MAX_PANELS:
                break
            currency = str(raw_currency or "").strip().upper()
            if not currency or currency == base_currency or currency in seen:
                continue
            seen.add(currency)
            scale = Decimal(display_scale(currency))
            nbrb_rows = self.currency_service.get_rate_history(
                user_id=user_id,
                currency=currency,
                limit=32,
                date_from=date_from,
                date_to=as_of,
                sources=NBRB_RATE_SOURCES,
            )
            bank_rows = self.bank_rate_service.get_user_rate_history(
                user_id=user_id,
                currency=currency,
                bank_codes=bank_codes or None,
                date_from=date_from,
                date_to=as_of,
                limit=self.PERIOD_DAYS,
            )
            series = [
                CurrencyDigestChartSeries(
                    kind="nbrb",
                    label="НБРБ",
                    points=tuple(
                        CurrencyDigestChartPoint(
                            day=self._as_date(row["rate_date"]),
                            value=Decimal(row["rate"]) * scale,
                            source_label="НБРБ",
                        )
                        for row in nbrb_rows
                    ),
                )
            ]
            best_buy, best_sell = self._best_bank_points(bank_rows)
            if best_buy:
                series.append(
                    CurrencyDigestChartSeries(
                        kind="bank_buy",
                        label="Покупка банком",
                        points=tuple(best_buy),
                    )
                )
            if best_sell:
                series.append(
                    CurrencyDigestChartSeries(
                        kind="bank_sell",
                        label="Продажа банком",
                        points=tuple(best_sell),
                    )
                )
            panels.append(
                CurrencyDigestChartPanel(
                    currency=currency,
                    display_label=f"{int(scale)} {currency}" if scale > 1 else currency,
                    series=tuple(series),
                    position_summary=self._position_summary(
                        positions.get(currency),
                        currency=currency,
                        base_currency=base_currency,
                    ),
                )
            )
        return TelegramCurrencyDigestChartPayload(
            as_of=as_of,
            panels=tuple(panels),
            base_currency=base_currency,
            total_current_value=Decimal(overview.get("total_current_value") or 0),
            total_result_value=Decimal(overview.get("total_result_value") or 0),
        )

    @staticmethod
    def _as_date(value) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @staticmethod
    def _best_bank_points(
        rows: list[dict],
    ) -> tuple[list[CurrencyDigestChartPoint], list[CurrencyDigestChartPoint]]:
        by_day: dict[date, list[dict]] = defaultdict(list)
        for row in rows:
            by_day[TelegramCurrencyDigestChartDataService._as_date(row["rate_date"])].append(row)
        best_buy = []
        best_sell = []
        for day in sorted(by_day):
            day_rows = by_day[day]
            buy_row = max(day_rows, key=lambda item: Decimal(item["buy_rate"]))
            sell_row = min(day_rows, key=lambda item: Decimal(item["sell_rate"]))
            best_buy.append(
                CurrencyDigestChartPoint(
                    day=day,
                    value=Decimal(buy_row["buy_rate"]),
                    source_label=str(buy_row.get("bank_name") or "Банк"),
                )
            )
            best_sell.append(
                CurrencyDigestChartPoint(
                    day=day,
                    value=Decimal(sell_row["sell_rate"]),
                    source_label=str(sell_row.get("bank_name") or "Банк"),
                )
            )
        return best_buy, best_sell

    @staticmethod
    def _position_summary(
        row: dict | None,
        *,
        currency: str,
        base_currency: str,
    ) -> str | None:
        if not row:
            return None
        quantity = Decimal(row.get("quantity") or 0)
        current_value = Decimal(row.get("current_value") or 0)
        return f"Позиция {quantity:.2f} {currency} · оценка {current_value:.2f} {base_currency}"
