from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import re

from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_analytics_cache, invalidate_dashboard_summary_cache
from app.core.logging import log_background_job_event
from app.db.models import FxTrade
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository


MONEY_Q = Decimal("0.01")
RATE_Q = Decimal("0.000001")
QTY_Q = Decimal("0.000001")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class CurrencyService:
    DEFAULT_TRACKED_CURRENCIES = ["USD", "EUR"]

    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value or 0).quantize(MONEY_Q)

    @staticmethod
    def _qty(value) -> Decimal:
        return Decimal(value or 0).quantize(QTY_Q)

    @staticmethod
    def _rate(value) -> Decimal:
        return Decimal(value or 0).quantize(RATE_Q)

    @staticmethod
    def _select_display_rate_rows(
        latest_rows: tuple | list,
        *,
        today: date,
    ) -> tuple | None:
        if not latest_rows:
            return None
        current_row = latest_rows[0] if len(latest_rows) > 0 else None
        previous_row = latest_rows[1] if len(latest_rows) > 1 else None
        older_row = latest_rows[2] if len(latest_rows) > 2 else None
        if (
            current_row
            and previous_row
            and current_row.rate_date == today
            and Decimal(current_row.rate) == Decimal(previous_row.rate)
        ):
            return previous_row, older_row
        return current_row, previous_row

    def _normalize_currency(self, value: str) -> str:
        code = str(value or "").strip().upper()
        if not _CURRENCY_RE.match(code):
            raise ValueError("Currency must be a 3-letter ISO code")
        return code

    def _normalize_side(self, value: str) -> str:
        side = str(value or "").strip().lower()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        return side

    @staticmethod
    def _normalize_trade_kind(value: str | None) -> str:
        trade_kind = str(value or "manual").strip().lower()
        if trade_kind not in {"manual", "card_payment"}:
            raise ValueError("trade_kind must be manual or card_payment")
        return trade_kind

    @staticmethod
    def is_cashflow_trade(trade: FxTrade) -> bool:
        if getattr(trade, "linked_operation_id", None) is not None:
            return False
        return str(getattr(trade, "trade_kind", "manual") or "manual").strip().lower() != "card_payment"

    def _validate_trade_sequence(self, trades: list[FxTrade]) -> None:
        quantities_by_currency: dict[str, Decimal] = {}
        ordered = sorted(
            trades,
            key=lambda item: (
                str(item.asset_currency or ""),
                item.trade_date.isoformat() if item.trade_date else "",
                int(item.id or 0),
            ),
        )
        for trade in ordered:
            currency = self._normalize_currency(trade.asset_currency)
            quantity = self._qty(trade.quantity)
            available = quantities_by_currency.get(currency, Decimal("0"))
            if trade.side == "buy":
                quantities_by_currency[currency] = self._qty(available + quantity)
                continue
            if available < quantity:
                raise ValueError("Not enough currency balance to keep FX trade history consistent")
            quantities_by_currency[currency] = self._qty(available - quantity)

    def _apply_trade_to_position_state(
        self,
        *,
        positions_by_currency: dict[str, dict],
        realized_by_currency: dict[str, Decimal],
        trade_stats_by_currency: dict[str, dict] | None,
        trade: FxTrade,
        totals: dict[str, Decimal | int] | None = None,
    ) -> None:
        currency = self._normalize_currency(trade.asset_currency)
        position = positions_by_currency.setdefault(
            currency,
            {
                "currency": currency,
                "quantity": self._qty(0),
                "book_value": self._money(0),
                "average_buy_rate": self._rate(0),
                "realized_result_value": self._money(0),
            },
        )
        trade_stats = None
        if trade_stats_by_currency is not None:
            trade_stats = trade_stats_by_currency.setdefault(
                currency,
                {
                    "buy_trades_count": 0,
                    "sell_trades_count": 0,
                    "buy_volume_base": self._money(0),
                    "sell_volume_base": self._money(0),
                    "buy_quantity": self._qty(0),
                    "sell_quantity": self._qty(0),
                },
            )
        quantity = self._qty(trade.quantity)
        gross = Decimal(trade.quantity) * Decimal(trade.unit_price)
        fee = self._money(trade.fee)
        if trade.side == "buy":
            if totals is not None:
                totals["buy_trades"] = int(totals.get("buy_trades", 0)) + 1
                totals["buy_volume_base"] = self._money(Decimal(totals.get("buy_volume_base", 0)) + gross)
                totals["buy_quantity"] = self._qty(Decimal(totals.get("buy_quantity", 0)) + quantity)
            if trade_stats is not None:
                trade_stats["buy_trades_count"] += 1
                trade_stats["buy_volume_base"] = self._money(trade_stats["buy_volume_base"] + gross)
                trade_stats["buy_quantity"] = self._qty(trade_stats["buy_quantity"] + quantity)
            position["quantity"] = self._qty(position["quantity"] + quantity)
            position["book_value"] = self._money(position["book_value"] + gross + fee)
        else:
            if totals is not None:
                totals["sell_trades"] = int(totals.get("sell_trades", 0)) + 1
                totals["sell_volume_base"] = self._money(Decimal(totals.get("sell_volume_base", 0)) + gross)
                totals["sell_quantity"] = self._qty(Decimal(totals.get("sell_quantity", 0)) + quantity)
            if trade_stats is not None:
                trade_stats["sell_trades_count"] += 1
                trade_stats["sell_volume_base"] = self._money(trade_stats["sell_volume_base"] + gross)
                trade_stats["sell_quantity"] = self._qty(trade_stats["sell_quantity"] + quantity)
            current_quantity = Decimal(position["quantity"])
            if current_quantity <= 0 or current_quantity < quantity:
                raise ValueError(f"Broken FX history for {currency}: sell exceeds available quantity")
            avg_rate = Decimal(position["book_value"]) / current_quantity if current_quantity > 0 else Decimal("0")
            cost_basis = quantity * avg_rate
            proceeds = gross - fee
            realized = proceeds - cost_basis
            position["quantity"] = self._qty(current_quantity - quantity)
            position["book_value"] = self._money(Decimal(position["book_value"]) - cost_basis)
            position["realized_result_value"] = self._money(position["realized_result_value"] + realized)
            realized_by_currency[currency] = self._money(realized_by_currency.get(currency, Decimal("0")) + realized)
        remaining_quantity = Decimal(position["quantity"])
        position["average_buy_rate"] = self._rate(
            Decimal(position["book_value"]) / remaining_quantity if remaining_quantity > 0 else Decimal("0")
        )

    def get_currency_preferences(self, user_id: int) -> dict:
        prefs = self.preferences.get_or_create(user_id)
        raw = prefs.data.get("currency") if isinstance(prefs.data.get("currency"), dict) else {}
        tracked = raw.get("tracked_currencies")
        if not isinstance(tracked, list):
            tracked = list(self.DEFAULT_TRACKED_CURRENCIES)
        normalized = []
        for item in tracked:
            try:
                code = self._normalize_currency(str(item))
            except ValueError:
                continue
            if code not in normalized:
                normalized.append(code)
        return {
            "base_currency": self._normalize_currency(
                str((prefs.data.get("ui") or {}).get("currency") or "BYN")
            ),
            "tracked_currencies": normalized or list(self.DEFAULT_TRACKED_CURRENCIES),
            "show_dashboard_kpi": raw.get("show_dashboard_kpi", True) is not False,
            "telegram_digest_enabled": raw.get("telegram_digest_enabled", False) is True,
        }

    def create_trade(
        self,
        *,
        user_id: int,
        side: str,
        asset_currency: str,
        quote_currency: str,
        quantity,
        unit_price,
        fee,
        trade_kind: str = "manual",
        linked_operation_id: int | None = None,
        trade_date: date,
        note: str | None = None,
        commit: bool = True,
    ) -> FxTrade:
        normalized_side = self._normalize_side(side)
        normalized_asset = self._normalize_currency(asset_currency)
        normalized_quote = self._normalize_currency(quote_currency)
        normalized_quantity = self._qty(quantity)
        normalized_unit_price = self._rate(unit_price)
        normalized_fee = self._money(fee)
        normalized_trade_kind = self._normalize_trade_kind(trade_kind)
        if normalized_asset == normalized_quote:
            raise ValueError("asset_currency and quote_currency must differ")
        if normalized_quantity <= 0 or normalized_unit_price <= 0:
            raise ValueError("quantity and unit_price must be positive")

        trades = self.repo.list_all_trades(user_id=user_id)
        candidate = FxTrade(
            user_id=user_id,
            side=normalized_side,
            asset_currency=normalized_asset,
            quote_currency=normalized_quote,
            quantity=normalized_quantity,
            unit_price=normalized_unit_price,
            fee=normalized_fee,
            trade_kind=normalized_trade_kind,
            linked_operation_id=linked_operation_id,
            trade_date=trade_date,
            note=(note or "").strip() or None,
        )
        try:
            self._validate_trade_sequence([*trades, candidate])
        except ValueError as exc:
            if normalized_side == "sell":
                raise ValueError("Not enough currency balance to sell") from exc
            raise

        item = self.repo.create_trade(
            candidate
        )
        if commit:
            self.db.commit()
            self.db.refresh(item)
            invalidate_dashboard_summary_cache(user_id)
            invalidate_dashboard_analytics_cache(user_id)
            log_background_job_event(
                "currency_service",
                "fx_trade_created",
                user_id=user_id,
                fx_trade_id=item.id,
                side=item.side,
                asset_currency=item.asset_currency,
                quote_currency=item.quote_currency,
                trade_kind=item.trade_kind,
            )
        return item

    def update_trade(
        self,
        *,
        user_id: int,
        trade_id: int,
        side: str,
        asset_currency: str,
        quote_currency: str,
        quantity,
        unit_price,
        fee,
        trade_kind: str = "manual",
        linked_operation_id: int | None = None,
        trade_date: date,
        note: str | None = None,
        allow_linked_trade_update: bool = False,
    ) -> FxTrade:
        item = self.repo.get_trade(user_id=user_id, trade_id=trade_id)
        if not item:
            raise ValueError("Currency trade not found")
        if getattr(item, "linked_operation_id", None) is not None and not allow_linked_trade_update:
            raise ValueError("Linked settlement trade must be edited from the operation")
        normalized_side = self._normalize_side(side)
        normalized_asset = self._normalize_currency(asset_currency)
        normalized_quote = self._normalize_currency(quote_currency)
        normalized_quantity = self._qty(quantity)
        normalized_unit_price = self._rate(unit_price)
        normalized_fee = self._money(fee)
        normalized_trade_kind = self._normalize_trade_kind(trade_kind)
        if normalized_asset == normalized_quote:
            raise ValueError("asset_currency and quote_currency must differ")
        if normalized_quantity <= 0 or normalized_unit_price <= 0:
            raise ValueError("quantity and unit_price must be positive")
        trades = self.repo.list_all_trades(user_id=user_id)
        replacement = FxTrade(
            id=item.id,
            user_id=item.user_id,
            side=normalized_side,
            asset_currency=normalized_asset,
            quote_currency=normalized_quote,
            quantity=normalized_quantity,
            unit_price=normalized_unit_price,
            fee=normalized_fee,
            trade_kind=normalized_trade_kind,
            linked_operation_id=linked_operation_id,
            trade_date=trade_date,
            note=(note or "").strip() or None,
        )
        self._validate_trade_sequence([replacement if trade.id == item.id else trade for trade in trades])
        item.side = normalized_side
        item.asset_currency = normalized_asset
        item.quote_currency = normalized_quote
        item.quantity = normalized_quantity
        item.unit_price = normalized_unit_price
        item.fee = normalized_fee
        item.trade_kind = normalized_trade_kind
        item.linked_operation_id = linked_operation_id
        item.trade_date = trade_date
        item.note = (note or "").strip() or None
        self.db.commit()
        self.db.refresh(item)
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        log_background_job_event(
            "currency_service",
            "fx_trade_updated",
            user_id=user_id,
            fx_trade_id=item.id,
            side=item.side,
            asset_currency=item.asset_currency,
            quote_currency=item.quote_currency,
            trade_kind=item.trade_kind,
        )
        return item

    def sync_linked_operation_trade(
        self,
        *,
        user_id: int,
        operation_id: int,
        asset_currency: str,
        quote_currency: str,
        quantity,
        unit_price,
        trade_date: date,
        note: str | None = None,
        commit: bool = False,
    ) -> FxTrade:
        existing = self.repo.get_trade_by_linked_operation_id(user_id=user_id, operation_id=operation_id)
        if existing:
            return self.update_trade(
                user_id=user_id,
                trade_id=existing.id,
                side="sell",
                asset_currency=asset_currency,
                quote_currency=quote_currency,
                quantity=quantity,
                unit_price=unit_price,
                fee=Decimal("0"),
                trade_kind="card_payment",
                linked_operation_id=operation_id,
                trade_date=trade_date,
                note=note,
                allow_linked_trade_update=True,
            )
        return self.create_trade(
            user_id=user_id,
            side="sell",
            asset_currency=asset_currency,
            quote_currency=quote_currency,
            quantity=quantity,
            unit_price=unit_price,
            fee=Decimal("0"),
            trade_kind="card_payment",
            linked_operation_id=operation_id,
            trade_date=trade_date,
            note=note,
            commit=commit,
        )

    def delete_trade(self, *, user_id: int, trade_id: int) -> None:
        item = self.repo.get_trade(user_id=user_id, trade_id=trade_id)
        if not item:
            raise ValueError("Currency trade not found")
        if getattr(item, "linked_operation_id", None) is not None:
            raise ValueError("Linked settlement trade must be deleted from the operation")
        item_side = item.side
        item_asset_currency = item.asset_currency
        item_quote_currency = item.quote_currency
        trades = self.repo.list_all_trades(user_id=user_id)
        self._validate_trade_sequence([trade for trade in trades if trade.id != item.id])
        self.repo.delete_trade(item)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        log_background_job_event(
            "currency_service",
            "fx_trade_deleted",
            user_id=user_id,
            fx_trade_id=trade_id,
            side=item_side,
            asset_currency=item_asset_currency,
            quote_currency=item_quote_currency,
        )

    def upsert_rate(self, *, user_id: int, currency: str, rate, rate_date: date, source: str = "manual") -> dict:
        normalized_currency = self._normalize_currency(currency)
        normalized_rate = self._rate(rate)
        if normalized_rate <= 0:
            raise ValueError("rate must be positive")
        item = self.repo.upsert_rate(
            user_id=user_id,
            currency=normalized_currency,
            rate_date=rate_date,
            rate=normalized_rate,
            source=(source or "manual").strip() or "manual",
        )
        self.db.commit()
        self.db.refresh(item)
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        log_background_job_event(
            "currency_service",
            "fx_rate_upserted",
            user_id=user_id,
            currency=item.currency,
            rate_date=item.rate_date.isoformat(),
            source=item.source,
        )
        return {
            "currency": item.currency,
            "rate": self._rate(item.rate),
            "rate_date": item.rate_date,
            "source": item.source,
        }

    def compute_positions(self, *, user_id: int) -> dict:
        prefs = self.get_currency_preferences(user_id)
        latest_rate_triplets = self.repo.get_latest_rate_triplet_map(user_id=user_id)
        latest_rates = {}
        for currency, rows in latest_rate_triplets.items():
            selected = self._select_display_rate_rows(rows, today=date.today())
            if selected and selected[0]:
                latest_rates[currency] = selected[0]
        trades = self.repo.list_all_trades(user_id=user_id)
        positions_by_currency: dict[str, dict] = {}
        realized_by_currency: dict[str, Decimal] = {}
        trade_stats_by_currency: dict[str, dict] = {}
        totals = {
            "buy_volume_base": self._money(0),
            "sell_volume_base": self._money(0),
            "buy_trades": 0,
            "sell_trades": 0,
            "buy_quantity": self._qty(0),
            "sell_quantity": self._qty(0),
        }

        for trade in trades:
            self._apply_trade_to_position_state(
                positions_by_currency=positions_by_currency,
                realized_by_currency=realized_by_currency,
                trade_stats_by_currency=trade_stats_by_currency,
                trade=trade,
                totals=totals,
            )

        positions = []
        total_book_value = self._money(0)
        total_current_value = self._money(0)
        total_result_value = self._money(0)
        total_realized_result_value = self._money(sum(realized_by_currency.values(), start=Decimal("0")))
        for currency, raw in sorted(positions_by_currency.items()):
            quantity = self._qty(raw["quantity"])
            if quantity <= 0:
                continue
            rate_row = latest_rates.get(currency)
            current_rate = self._rate(rate_row.rate if rate_row else raw["average_buy_rate"])
            current_value = self._money(Decimal(quantity) * Decimal(current_rate))
            book_value = self._money(raw["book_value"])
            result_value = self._money(current_value - book_value)
            result_pct = None
            if book_value > 0:
                result_pct = float((Decimal(result_value) / Decimal(book_value)) * Decimal("100"))
            positions.append(
                {
                    "currency": currency,
                    "quantity": quantity,
                    "average_buy_rate": self._rate(raw["average_buy_rate"]),
                    "book_value": book_value,
                    "current_rate": current_rate,
                    "current_rate_date": rate_row.rate_date.isoformat() if rate_row else None,
                    "current_value": current_value,
                    "result_value": result_value,
                    "result_pct": result_pct,
                    "realized_result_value": self._money(raw["realized_result_value"]),
                    "total_result_value": self._money(Decimal(raw["realized_result_value"]) + Decimal(result_value)),
                }
            )
            total_book_value += book_value
            total_current_value += current_value
            total_result_value += result_value

        recent_trades = [
            {
                "id": trade.id,
                "side": trade.side,
                "asset_currency": trade.asset_currency,
                "quote_currency": trade.quote_currency,
                "quantity": self._qty(trade.quantity),
                "unit_price": self._rate(trade.unit_price),
                "fee": self._money(trade.fee),
                "trade_kind": getattr(trade, "trade_kind", "manual") or "manual",
                "linked_operation_id": getattr(trade, "linked_operation_id", None),
                "trade_date": trade.trade_date,
                "note": trade.note,
                "created_at": trade.created_at,
            }
            for trade in trades
        ]
        return {
            "base_currency": prefs["base_currency"],
            "tracked_currencies": prefs["tracked_currencies"],
            "show_dashboard_kpi": prefs["show_dashboard_kpi"],
            "telegram_digest_enabled": prefs["telegram_digest_enabled"],
            "active_positions": len(positions),
            "total_book_value": self._money(total_book_value),
            "total_current_value": self._money(total_current_value),
            "total_result_value": self._money(total_result_value),
            "total_unrealized_result_value": self._money(total_result_value),
            "total_realized_result_value": total_realized_result_value,
            "total_combined_result_value": self._money(Decimal(total_result_value) + Decimal(total_realized_result_value)),
            "buy_trades_count": int(totals["buy_trades"]),
            "sell_trades_count": int(totals["sell_trades"]),
            "buy_volume_base": self._money(totals["buy_volume_base"]),
            "sell_volume_base": self._money(totals["sell_volume_base"]),
            "buy_quantity": self._qty(totals["buy_quantity"]),
            "sell_quantity": self._qty(totals["sell_quantity"]),
            "buy_average_rate": self._rate(Decimal(totals["buy_volume_base"]) / Decimal(totals["buy_quantity"])) if Decimal(totals["buy_quantity"]) > 0 else self._rate(0),
            "sell_average_rate": self._rate(Decimal(totals["sell_volume_base"]) / Decimal(totals["sell_quantity"])) if Decimal(totals["sell_quantity"]) > 0 else self._rate(0),
            "positions": positions,
            "positions_by_currency": {item["currency"]: item for item in positions},
            "realized_by_currency": {key: self._money(value) for key, value in realized_by_currency.items()},
            "trade_stats_by_currency": trade_stats_by_currency,
            "current_rates": [
                {
                    "currency": current_row.currency,
                    "rate": self._rate(current_row.rate),
                    "rate_date": current_row.rate_date,
                    "source": current_row.source,
                    "previous_rate": self._rate(previous_row.rate) if previous_row else None,
                    "change_value": (
                        self._rate(Decimal(current_row.rate) - Decimal(previous_row.rate))
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
                    "average_buy_rate": self._rate(
                        Decimal(trade_stats_by_currency.get(current_row.currency, {}).get("buy_volume_base", 0))
                        / Decimal(trade_stats_by_currency.get(current_row.currency, {}).get("buy_quantity", 0))
                    ) if Decimal(trade_stats_by_currency.get(current_row.currency, {}).get("buy_quantity", 0)) > 0 else self._rate(0),
                    "average_sell_rate": self._rate(
                        Decimal(trade_stats_by_currency.get(current_row.currency, {}).get("sell_volume_base", 0))
                        / Decimal(trade_stats_by_currency.get(current_row.currency, {}).get("sell_quantity", 0))
                    ) if Decimal(trade_stats_by_currency.get(current_row.currency, {}).get("sell_quantity", 0)) > 0 else self._rate(0),
                }
                for rows in latest_rate_triplets.values()
                for current_row, previous_row in [self._select_display_rate_rows(rows, today=date.today())]
                if current_row
            ],
        }

    def get_overview(self, *, user_id: int, currency: str | None = None, trades_limit: int = 100) -> dict:
        normalized_currency = self._normalize_currency(currency) if currency else None
        computed = self.compute_positions(user_id=user_id)
        trades = self.repo.list_trades(user_id=user_id, asset_currency=normalized_currency, limit=trades_limit)
        recent_trades = [
            {
                "id": trade.id,
                "side": trade.side,
                "asset_currency": trade.asset_currency,
                "quote_currency": trade.quote_currency,
                "quantity": self._qty(trade.quantity),
                "unit_price": self._rate(trade.unit_price),
                "fee": self._money(trade.fee),
                "trade_kind": getattr(trade, "trade_kind", "manual") or "manual",
                "linked_operation_id": getattr(trade, "linked_operation_id", None),
                "trade_date": trade.trade_date,
                "note": trade.note,
                "created_at": trade.created_at,
            }
            for trade in trades
        ]
        positions = computed["positions"]
        if normalized_currency:
            positions = [item for item in positions if item["currency"] == normalized_currency]
        current_rates = computed["current_rates"]
        if normalized_currency:
            current_rates = [item for item in current_rates if item["currency"] == normalized_currency]
        trade_stats = (
            computed["trade_stats_by_currency"].get(
                normalized_currency,
                {
                "buy_trades_count": 0,
                "sell_trades_count": 0,
                "buy_volume_base": self._money(0),
                "sell_volume_base": self._money(0),
                "buy_quantity": self._qty(0),
                "sell_quantity": self._qty(0),
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
        buy_average_rate = self._rate(Decimal(trade_stats["buy_volume_base"]) / buy_quantity) if buy_quantity > 0 else self._rate(0)
        sell_quantity = Decimal(trade_stats["sell_quantity"])
        sell_average_rate = self._rate(Decimal(trade_stats["sell_volume_base"]) / sell_quantity) if sell_quantity > 0 else self._rate(0)
        return {
            "base_currency": computed["base_currency"],
            "tracked_currencies": computed["tracked_currencies"],
            "active_positions": len(positions),
            "total_book_value": self._money(sum(Decimal(item["book_value"]) for item in positions)),
            "total_current_value": self._money(sum(Decimal(item["current_value"]) for item in positions)),
            "total_result_value": self._money(sum(Decimal(item["result_value"]) for item in positions)),
            "total_unrealized_result_value": self._money(sum(Decimal(item["result_value"]) for item in positions)),
            "total_realized_result_value": (
                self._money(Decimal(computed["realized_by_currency"].get(normalized_currency, Decimal("0"))))
                if normalized_currency
                else computed["total_realized_result_value"]
            ),
            "total_combined_result_value": (
                self._money(
                    sum(Decimal(item["result_value"]) for item in positions)
                    + Decimal(computed["realized_by_currency"].get(normalized_currency, Decimal("0")))
                )
                if normalized_currency
                else self._money(
                    Decimal(computed["total_unrealized_result_value"]) + Decimal(computed["total_realized_result_value"])
                )
            ),
            "buy_trades_count": int(trade_stats["buy_trades_count"]),
            "sell_trades_count": int(trade_stats["sell_trades_count"]),
            "buy_volume_base": self._money(trade_stats["buy_volume_base"]),
            "sell_volume_base": self._money(trade_stats["sell_volume_base"]),
            "buy_average_rate": self._rate(buy_average_rate),
            "sell_average_rate": self._rate(sell_average_rate),
            "positions": positions,
            "recent_trades": recent_trades,
            "current_rates": current_rates,
        }

    def get_performance_history(
        self,
        *,
        user_id: int,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        normalized_currency = self._normalize_currency(currency) if currency else None
        prefs = self.get_currency_preferences(user_id)
        resolved_to = date_to or date.today()
        all_trades = self.repo.list_all_trades(user_id=user_id)
        relevant_trades = [
            trade for trade in all_trades
            if trade.trade_date <= resolved_to and (normalized_currency is None or trade.asset_currency == normalized_currency)
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

        resolved_from = date_from or min(trade.trade_date for trade in relevant_trades)
        timeline_start = min(trade.trade_date for trade in relevant_trades)
        relevant_currencies = sorted({self._normalize_currency(trade.asset_currency) for trade in relevant_trades})
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
                latest_rate_by_currency[self._normalize_currency(row.currency)] = self._rate(row.rate)
            for trade in trades_by_date.get(current_date, []):
                self._apply_trade_to_position_state(
                    positions_by_currency=positions_by_currency,
                    realized_by_currency=realized_by_currency,
                    trade_stats_by_currency=None,
                    trade=trade,
                )
            if current_date >= resolved_from:
                book_value = self._money(0)
                current_value = self._money(0)
                for current_currency, raw in positions_by_currency.items():
                    quantity = self._qty(raw["quantity"])
                    if quantity <= 0:
                        continue
                    rate = latest_rate_by_currency.get(current_currency)
                    effective_rate = self._rate(rate if rate is not None else raw["average_buy_rate"])
                    book_value += self._money(raw["book_value"])
                    current_value += self._money(Decimal(quantity) * Decimal(effective_rate))
                realized_total = self._money(sum(realized_by_currency.values(), start=Decimal("0")))
                unrealized_total = self._money(Decimal(current_value) - Decimal(book_value))
                points.append(
                    {
                        "point_date": current_date,
                        "book_value": self._money(book_value),
                        "current_value": self._money(current_value),
                        "unrealized_result_value": unrealized_total,
                        "realized_result_value": realized_total,
                        "total_result_value": self._money(Decimal(realized_total) + Decimal(unrealized_total)),
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
        normalized_currency = self._normalize_currency(currency)
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
                "rate": self._rate(row.rate),
                "rate_date": row.rate_date,
            }
            for row in rows
        ]
