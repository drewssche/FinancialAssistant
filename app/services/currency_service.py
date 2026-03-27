from datetime import date
from decimal import Decimal
import re

from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_summary_cache
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
        trade_date: date,
        note: str | None = None,
    ) -> FxTrade:
        normalized_side = self._normalize_side(side)
        normalized_asset = self._normalize_currency(asset_currency)
        normalized_quote = self._normalize_currency(quote_currency)
        normalized_quantity = self._qty(quantity)
        normalized_unit_price = self._rate(unit_price)
        normalized_fee = self._money(fee)
        if normalized_asset == normalized_quote:
            raise ValueError("asset_currency and quote_currency must differ")
        if normalized_quantity <= 0 or normalized_unit_price <= 0:
            raise ValueError("quantity and unit_price must be positive")

        positions = self.compute_positions(user_id=user_id)
        if normalized_side == "sell":
            current = positions["positions_by_currency"].get(normalized_asset)
            if not current or current["quantity"] < normalized_quantity:
                raise ValueError("Not enough currency balance to sell")

        item = self.repo.create_trade(
            FxTrade(
                user_id=user_id,
                side=normalized_side,
                asset_currency=normalized_asset,
                quote_currency=normalized_quote,
                quantity=normalized_quantity,
                unit_price=normalized_unit_price,
                fee=normalized_fee,
                trade_date=trade_date,
                note=(note or "").strip() or None,
            )
        )
        self.db.commit()
        self.db.refresh(item)
        invalidate_dashboard_summary_cache(user_id)
        log_background_job_event(
            "currency_service",
            "fx_trade_created",
            user_id=user_id,
            fx_trade_id=item.id,
            side=item.side,
            asset_currency=item.asset_currency,
            quote_currency=item.quote_currency,
        )
        return item

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
        latest_rate_pairs = self.repo.get_latest_rate_pair_map(user_id=user_id)
        latest_rates = {currency: pair[0] for currency, pair in latest_rate_pairs.items()}
        trades = self.repo.list_all_trades(user_id=user_id)
        positions_by_currency: dict[str, dict] = {}
        realized_by_currency: dict[str, Decimal] = {}
        trade_stats_by_currency: dict[str, dict] = {}
        total_buy_volume_base = self._money(0)
        total_sell_volume_base = self._money(0)
        total_buy_trades = 0
        total_sell_trades = 0

        for trade in trades:
            currency = trade.asset_currency
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
            trade_stats = trade_stats_by_currency.setdefault(
                currency,
                {
                    "buy_trades_count": 0,
                    "sell_trades_count": 0,
                    "buy_volume_base": self._money(0),
                    "sell_volume_base": self._money(0),
                },
            )
            quantity = self._qty(trade.quantity)
            gross = Decimal(trade.quantity) * Decimal(trade.unit_price)
            fee = self._money(trade.fee)
            if trade.side == "buy":
                total_buy_trades += 1
                total_buy_volume_base = self._money(total_buy_volume_base + gross)
                trade_stats["buy_trades_count"] += 1
                trade_stats["buy_volume_base"] = self._money(trade_stats["buy_volume_base"] + gross)
                position["quantity"] = self._qty(position["quantity"] + quantity)
                position["book_value"] = self._money(position["book_value"] + gross + fee)
            else:
                total_sell_trades += 1
                total_sell_volume_base = self._money(total_sell_volume_base + gross)
                trade_stats["sell_trades_count"] += 1
                trade_stats["sell_volume_base"] = self._money(trade_stats["sell_volume_base"] + gross)
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

        positions = []
        total_book_value = self._money(0)
        total_current_value = self._money(0)
        total_result_value = self._money(0)
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
            "total_book_value": self._money(total_book_value),
            "total_current_value": self._money(total_current_value),
            "total_result_value": self._money(total_result_value),
            "buy_trades_count": total_buy_trades,
            "sell_trades_count": total_sell_trades,
            "buy_volume_base": self._money(total_buy_volume_base),
            "sell_volume_base": self._money(total_sell_volume_base),
            "positions": positions,
            "positions_by_currency": {item["currency"]: item for item in positions},
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
                }
                for current_row, previous_row in latest_rate_pairs.values()
            ],
        }

    def get_overview(self, *, user_id: int, currency: str | None = None, trades_limit: int = 100) -> dict:
        normalized_currency = self._normalize_currency(currency) if currency else None
        computed = self.compute_positions(user_id=user_id)
        trades = self.repo.list_trades(user_id=user_id, asset_currency=normalized_currency, limit=trades_limit)
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
                },
            )
            if normalized_currency
            else {
                "buy_trades_count": computed["buy_trades_count"],
                "sell_trades_count": computed["sell_trades_count"],
                "buy_volume_base": computed["buy_volume_base"],
                "sell_volume_base": computed["sell_volume_base"],
            }
        )
        return {
            "base_currency": computed["base_currency"],
            "tracked_currencies": computed["tracked_currencies"],
            "active_positions": len(positions),
            "total_book_value": self._money(sum(Decimal(item["book_value"]) for item in positions)),
            "total_current_value": self._money(sum(Decimal(item["current_value"]) for item in positions)),
            "total_result_value": self._money(sum(Decimal(item["result_value"]) for item in positions)),
            "buy_trades_count": int(trade_stats["buy_trades_count"]),
            "sell_trades_count": int(trade_stats["sell_trades_count"]),
            "buy_volume_base": self._money(trade_stats["buy_volume_base"]),
            "sell_volume_base": self._money(trade_stats["sell_volume_base"]),
            "positions": positions,
            "recent_trades": trades,
            "current_rates": current_rates,
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
