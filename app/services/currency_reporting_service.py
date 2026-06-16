from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.db.models import FxTrade


class CurrencyReportingService:
    """Builds currency portfolio, trade-list, and history read models."""

    def __init__(self, currency_service):
        self.currency = currency_service
        self.repo = currency_service.repo

    def compute_positions(self, *, user_id: int) -> dict:
        service = self.currency
        prefs = service.get_currency_preferences(user_id)
        latest_rate_triplets = self.repo.get_latest_rate_triplet_map(user_id=user_id)
        latest_rates = {}
        for currency, rows in latest_rate_triplets.items():
            selected = service._select_display_rate_rows(rows, today=date.today())
            if selected and selected[0]:
                latest_rates[currency] = selected[0]
        trades = self.repo.list_all_trades(user_id=user_id)
        positions_by_currency: dict[str, dict] = {}
        realized_by_currency: dict[str, Decimal] = {}
        trade_stats_by_currency: dict[str, dict] = {}
        totals = {
            "buy_volume_base": service._money(0),
            "sell_volume_base": service._money(0),
            "buy_trades": 0,
            "sell_trades": 0,
            "buy_quantity": service._qty(0),
            "sell_quantity": service._qty(0),
        }

        for trade in trades:
            service._apply_trade_to_position_state(
                positions_by_currency=positions_by_currency,
                realized_by_currency=realized_by_currency,
                trade_stats_by_currency=trade_stats_by_currency,
                trade=trade,
                totals=totals,
            )

        positions = []
        total_book_value = service._money(0)
        total_current_value = service._money(0)
        total_result_value = service._money(0)
        total_realized_result_value = service._money(
            sum(realized_by_currency.values(), start=Decimal("0"))
        )
        for currency, raw in sorted(positions_by_currency.items()):
            quantity = service._qty(raw["quantity"])
            if quantity <= 0:
                continue
            rate_row = latest_rates.get(currency)
            current_rate = service._rate(rate_row.rate if rate_row else raw["average_buy_rate"])
            current_value = service._money(Decimal(quantity) * Decimal(current_rate))
            book_value = service._money(raw["book_value"])
            result_value = service._money(current_value - book_value)
            result_pct = None
            if book_value > 0:
                result_pct = float((Decimal(result_value) / Decimal(book_value)) * Decimal("100"))
            positions.append(
                {
                    "currency": currency,
                    "quantity": quantity,
                    "average_buy_rate": service._rate(raw["average_buy_rate"]),
                    "book_value": book_value,
                    "current_rate": current_rate,
                    "current_rate_date": rate_row.rate_date.isoformat() if rate_row else None,
                    "current_value": current_value,
                    "result_value": result_value,
                    "result_pct": result_pct,
                    "realized_result_value": service._money(raw["realized_result_value"]),
                    "total_result_value": service._money(
                        Decimal(raw["realized_result_value"]) + Decimal(result_value)
                    ),
                }
            )
            total_book_value += book_value
            total_current_value += current_value
            total_result_value += result_value

        return {
            "base_currency": prefs["base_currency"],
            "tracked_currencies": prefs["tracked_currencies"],
            "show_dashboard_kpi": prefs["show_dashboard_kpi"],
            "telegram_digest_enabled": prefs["telegram_digest_enabled"],
            "active_positions": len(positions),
            "total_book_value": service._money(total_book_value),
            "total_current_value": service._money(total_current_value),
            "total_result_value": service._money(total_result_value),
            "total_unrealized_result_value": service._money(total_result_value),
            "total_realized_result_value": total_realized_result_value,
            "total_combined_result_value": service._money(
                Decimal(total_result_value) + Decimal(total_realized_result_value)
            ),
            "buy_trades_count": int(totals["buy_trades"]),
            "sell_trades_count": int(totals["sell_trades"]),
            "buy_volume_base": service._money(totals["buy_volume_base"]),
            "sell_volume_base": service._money(totals["sell_volume_base"]),
            "buy_quantity": service._qty(totals["buy_quantity"]),
            "sell_quantity": service._qty(totals["sell_quantity"]),
            "buy_average_rate": (
                service._rate(
                    Decimal(totals["buy_volume_base"]) / Decimal(totals["buy_quantity"])
                )
                if Decimal(totals["buy_quantity"]) > 0
                else service._rate(0)
            ),
            "sell_average_rate": (
                service._rate(
                    Decimal(totals["sell_volume_base"]) / Decimal(totals["sell_quantity"])
                )
                if Decimal(totals["sell_quantity"]) > 0
                else service._rate(0)
            ),
            "positions": positions,
            "positions_by_currency": {item["currency"]: item for item in positions},
            "realized_by_currency": {
                key: service._money(value) for key, value in realized_by_currency.items()
            },
            "trade_stats_by_currency": trade_stats_by_currency,
            "current_rates": [
                {
                    "currency": current_row.currency,
                    "rate": service._rate(current_row.rate),
                    "rate_date": current_row.rate_date,
                    "source": current_row.source,
                    "previous_rate": (
                        service._rate(previous_row.rate) if previous_row else None
                    ),
                    "change_value": (
                        service._rate(Decimal(current_row.rate) - Decimal(previous_row.rate))
                        if previous_row
                        else None
                    ),
                    "change_pct": (
                        float(
                            (
                                (Decimal(current_row.rate) - Decimal(previous_row.rate))
                                / Decimal(previous_row.rate)
                            )
                            * Decimal("100")
                        )
                        if previous_row and Decimal(previous_row.rate) > 0
                        else None
                    ),
                    "average_buy_rate": (
                        service._rate(
                            Decimal(
                                trade_stats_by_currency.get(
                                    current_row.currency, {}
                                ).get("buy_volume_base", 0)
                            )
                            / Decimal(
                                trade_stats_by_currency.get(
                                    current_row.currency, {}
                                ).get("buy_quantity", 0)
                            )
                        )
                        if Decimal(
                            trade_stats_by_currency.get(current_row.currency, {}).get(
                                "buy_quantity", 0
                            )
                        )
                        > 0
                        else service._rate(0)
                    ),
                    "average_sell_rate": (
                        service._rate(
                            Decimal(
                                trade_stats_by_currency.get(
                                    current_row.currency, {}
                                ).get("sell_volume_base", 0)
                            )
                            / Decimal(
                                trade_stats_by_currency.get(
                                    current_row.currency, {}
                                ).get("sell_quantity", 0)
                            )
                        )
                        if Decimal(
                            trade_stats_by_currency.get(current_row.currency, {}).get(
                                "sell_quantity", 0
                            )
                        )
                        > 0
                        else service._rate(0)
                    ),
                }
                for rows in latest_rate_triplets.values()
                for current_row, previous_row in [
                    service._select_display_rate_rows(rows, today=date.today())
                ]
                if current_row
            ],
        }

    def get_overview(
        self,
        *,
        user_id: int,
        currency: str | None = None,
        trades_limit: int = 100,
    ) -> dict:
        service = self.currency
        normalized_currency = service._normalize_currency(currency) if currency else None
        computed = self.compute_positions(user_id=user_id)
        trades = self.repo.list_trades(
            user_id=user_id,
            asset_currency=normalized_currency,
            limit=trades_limit,
        )
        recent_trades = [self._serialize_trade(trade) for trade in trades]
        positions = computed["positions"]
        if normalized_currency:
            positions = [
                item for item in positions if item["currency"] == normalized_currency
            ]
        current_rates = computed["current_rates"]
        if normalized_currency:
            current_rates = [
                item
                for item in current_rates
                if item["currency"] == normalized_currency
            ]
        trade_stats = (
            computed["trade_stats_by_currency"].get(
                normalized_currency,
                {
                    "buy_trades_count": 0,
                    "sell_trades_count": 0,
                    "buy_volume_base": service._money(0),
                    "sell_volume_base": service._money(0),
                    "buy_quantity": service._qty(0),
                    "sell_quantity": service._qty(0),
                },
            )
            if normalized_currency
            else {
                "buy_trades_count": computed["buy_trades_count"],
                "sell_trades_count": computed["sell_trades_count"],
                "buy_volume_base": computed["buy_volume_base"],
                "sell_volume_base": computed["sell_volume_base"],
                "buy_quantity": computed["buy_quantity"],
                "sell_quantity": computed["sell_quantity"],
            }
        )
        buy_quantity = Decimal(trade_stats["buy_quantity"])
        buy_average_rate = (
            service._rate(Decimal(trade_stats["buy_volume_base"]) / buy_quantity)
            if buy_quantity > 0
            else service._rate(0)
        )
        sell_quantity = Decimal(trade_stats["sell_quantity"])
        sell_average_rate = (
            service._rate(Decimal(trade_stats["sell_volume_base"]) / sell_quantity)
            if sell_quantity > 0
            else service._rate(0)
        )
        return {
            "base_currency": computed["base_currency"],
            "tracked_currencies": computed["tracked_currencies"],
            "active_positions": len(positions),
            "total_book_value": service._money(
                sum(Decimal(item["book_value"]) for item in positions)
            ),
            "total_current_value": service._money(
                sum(Decimal(item["current_value"]) for item in positions)
            ),
            "total_result_value": service._money(
                sum(Decimal(item["result_value"]) for item in positions)
            ),
            "total_unrealized_result_value": service._money(
                sum(Decimal(item["result_value"]) for item in positions)
            ),
            "total_realized_result_value": (
                service._money(
                    Decimal(
                        computed["realized_by_currency"].get(
                            normalized_currency, Decimal("0")
                        )
                    )
                )
                if normalized_currency
                else computed["total_realized_result_value"]
            ),
            "total_combined_result_value": (
                service._money(
                    sum(Decimal(item["result_value"]) for item in positions)
                    + Decimal(
                        computed["realized_by_currency"].get(
                            normalized_currency, Decimal("0")
                        )
                    )
                )
                if normalized_currency
                else service._money(
                    Decimal(computed["total_unrealized_result_value"])
                    + Decimal(computed["total_realized_result_value"])
                )
            ),
            "buy_trades_count": int(trade_stats["buy_trades_count"]),
            "sell_trades_count": int(trade_stats["sell_trades_count"]),
            "buy_volume_base": service._money(trade_stats["buy_volume_base"]),
            "sell_volume_base": service._money(trade_stats["sell_volume_base"]),
            "buy_average_rate": service._rate(buy_average_rate),
            "sell_average_rate": service._rate(sell_average_rate),
            "positions": positions,
            "recent_trades": recent_trades,
            "current_rates": current_rates,
        }

    def list_trades(
        self,
        *,
        user_id: int,
        currency: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        normalized_currency = (
            self.currency._normalize_currency(currency) if currency else None
        )
        items, total = self.repo.list_trades_paginated(
            user_id=user_id,
            asset_currency=normalized_currency,
            page=page,
            page_size=page_size,
        )
        return {
            "items": [self._serialize_trade(trade) for trade in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_performance_history(
        self,
        *,
        user_id: int,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        service = self.currency
        normalized_currency = service._normalize_currency(currency) if currency else None
        prefs = service.get_currency_preferences(user_id)
        resolved_to = date_to or date.today()
        all_trades = self.repo.list_all_trades(user_id=user_id)
        relevant_trades = [
            trade
            for trade in all_trades
            if trade.trade_date <= resolved_to
            and (
                normalized_currency is None
                or trade.asset_currency == normalized_currency
            )
        ]
        if not relevant_trades:
            resolved_from = date_from or resolved_to
            return {
                "base_currency": prefs["base_currency"],
                "currency": normalized_currency,
                "date_from": resolved_from,
                "date_to": resolved_to,
                "points": [],
            }

        resolved_from = date_from or min(
            trade.trade_date for trade in relevant_trades
        )
        timeline_start = min(trade.trade_date for trade in relevant_trades)
        relevant_currencies = sorted(
            {
                service._normalize_currency(trade.asset_currency)
                for trade in relevant_trades
            }
        )
        rate_rows = self.repo.list_rate_history_for_currencies(
            user_id=user_id,
            currencies=relevant_currencies,
            date_to=resolved_to,
        )
        trades_by_date: dict[date, list[FxTrade]] = defaultdict(list)
        for trade in relevant_trades:
            trades_by_date[trade.trade_date].append(trade)
        rates_by_date: dict[date, list] = defaultdict(list)
        for row in rate_rows:
            rates_by_date[row.rate_date].append(row)

        points: list[dict] = []
        positions_by_currency: dict[str, dict] = {}
        realized_by_currency: dict[str, Decimal] = {}
        latest_rate_by_currency: dict[str, Decimal] = {}
        current_date = timeline_start
        while current_date <= resolved_to:
            for row in rates_by_date.get(current_date, []):
                latest_rate_by_currency[service._normalize_currency(row.currency)] = (
                    service._rate(row.rate)
                )
            for trade in trades_by_date.get(current_date, []):
                service._apply_trade_to_position_state(
                    positions_by_currency=positions_by_currency,
                    realized_by_currency=realized_by_currency,
                    trade_stats_by_currency=None,
                    trade=trade,
                )
            if current_date >= resolved_from:
                book_value = service._money(0)
                current_value = service._money(0)
                for current_currency, raw in positions_by_currency.items():
                    quantity = service._qty(raw["quantity"])
                    if quantity <= 0:
                        continue
                    rate = latest_rate_by_currency.get(current_currency)
                    effective_rate = service._rate(
                        rate if rate is not None else raw["average_buy_rate"]
                    )
                    book_value += service._money(raw["book_value"])
                    current_value += service._money(
                        Decimal(quantity) * Decimal(effective_rate)
                    )
                realized_total = service._money(
                    sum(realized_by_currency.values(), start=Decimal("0"))
                )
                unrealized_total = service._money(
                    Decimal(current_value) - Decimal(book_value)
                )
                points.append(
                    {
                        "point_date": current_date,
                        "book_value": service._money(book_value),
                        "current_value": service._money(current_value),
                        "unrealized_result_value": unrealized_total,
                        "realized_result_value": realized_total,
                        "total_result_value": service._money(
                            Decimal(realized_total) + Decimal(unrealized_total)
                        ),
                    }
                )
            current_date += timedelta(days=1)

        return {
            "base_currency": prefs["base_currency"],
            "currency": normalized_currency,
            "date_from": resolved_from,
            "date_to": resolved_to,
            "points": points,
        }

    def get_rate_history(
        self,
        *,
        user_id: int,
        currency: str,
        limit: int = 120,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        service = self.currency
        normalized_currency = service._normalize_currency(currency)
        rows = self.repo.list_rate_history(
            user_id=user_id,
            currency=normalized_currency,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
        return [
            {
                "currency": row.currency,
                "rate": service._rate(row.rate),
                "rate_date": row.rate_date,
            }
            for row in rows
        ]

    def _serialize_trade(self, trade: FxTrade) -> dict:
        return {
            "id": trade.id,
            "side": trade.side,
            "asset_currency": trade.asset_currency,
            "quote_currency": trade.quote_currency,
            "quantity": self.currency._qty(trade.quantity),
            "unit_price": self.currency._rate(trade.unit_price),
            "fee": self.currency._money(trade.fee),
            "trade_kind": getattr(trade, "trade_kind", "manual") or "manual",
            "linked_operation_id": getattr(trade, "linked_operation_id", None),
            "trade_date": trade.trade_date,
            "note": trade.note,
            "created_at": trade.created_at,
        }
