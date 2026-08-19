from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import (
    invalidate_dashboard_analytics_cache,
    invalidate_dashboard_summary_cache,
    invalidate_plans_cache,
)
from app.core.logging import log_background_job_event
from app.db.models import FxTrade, Operation
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.services.activity_service import ActivityService
from app.services.bank_currency_rate_registry import (
    BANK_RATE_PROVIDERS,
    BANK_RATE_STALE_MINUTES,
    DEFAULT_BANK_RATE_BANKS,
)
from app.services.currency_reporting_service import CurrencyReportingService


MONEY_Q = Decimal("0.01")
RATE_Q = Decimal("0.000001")
QTY_Q = Decimal("0.000001")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_CURRENCY_ALIASES = {
    "RU": "RUB",
}


class CurrencyService:
    DEFAULT_TRACKED_CURRENCIES = ["USD", "EUR"]
    DEFAULT_BANK_RATE_BANKS = list(DEFAULT_BANK_RATE_BANKS)
    TRADE_FIELDS = ["side", "asset_currency", "quote_currency", "quantity", "unit_price", "fee", "trade_kind", "trade_date", "note"]
    TRADE_LABELS = {
        "side": "Тип сделки",
        "asset_currency": "Валюта",
        "quote_currency": "Валюта расчета",
        "quantity": "Количество",
        "unit_price": "Курс",
        "fee": "Комиссия",
        "trade_kind": "Источник",
        "trade_date": "Дата",
        "note": "Комментарий",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.activity = ActivityService(db)
        self.reporting = CurrencyReportingService(self)

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
        raw = str(value or "").strip().upper()
        code = _CURRENCY_ALIASES.get(raw, raw)
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

    def backfill_linked_card_payment_trades(
        self,
        *,
        commit: bool = False,
        max_created_at_delta_seconds: int = 600,
    ) -> int:
        trades = list(
            self.db.scalars(
                select(FxTrade)
                .where(
                    FxTrade.trade_kind.in_(("card_payment", "manual")),
                    FxTrade.linked_operation_id.is_(None),
                    FxTrade.side == "sell",
                )
                .order_by(FxTrade.user_id.asc(), FxTrade.trade_date.asc(), FxTrade.id.asc())
            )
        )
        if not trades:
            return 0
        already_linked_operation_ids = {
            int(item)
            for item in self.db.scalars(select(FxTrade.linked_operation_id).where(FxTrade.linked_operation_id.is_not(None)))
            if item is not None
        }
        linked_count = 0
        for trade in trades:
            quote_total = self._money(Decimal(trade.quantity or 0) * Decimal(trade.unit_price or 0))
            candidate_operations = [
                operation
                for operation in self.db.scalars(
                    select(Operation)
                    .where(
                        Operation.user_id == trade.user_id,
                        Operation.kind == "expense",
                        Operation.operation_date == trade.trade_date,
                        Operation.amount == quote_total,
                        Operation.base_currency == str(trade.quote_currency or "BYN").upper(),
                    )
                    .order_by(Operation.created_at.asc(), Operation.id.asc())
                )
                if int(operation.id) not in already_linked_operation_ids
            ]
            if len(candidate_operations) == 1:
                trade.linked_operation_id = int(candidate_operations[0].id)
                trade.trade_kind = "card_payment"
                already_linked_operation_ids.add(int(candidate_operations[0].id))
                linked_count += 1
                continue
            if len(candidate_operations) <= 1 or not max_created_at_delta_seconds:
                continue
            trade_created_at = getattr(trade, "created_at", None)
            if trade_created_at is None:
                continue
            nearby_matches = []
            for operation in candidate_operations:
                operation_created_at = getattr(operation, "created_at", None)
                if operation_created_at is None:
                    continue
                delta_seconds = abs((operation_created_at - trade_created_at).total_seconds())
                if delta_seconds <= max_created_at_delta_seconds:
                    nearby_matches.append((delta_seconds, operation))
            if len(nearby_matches) == 1:
                matched_operation = nearby_matches[0][1]
                trade.linked_operation_id = int(matched_operation.id)
                trade.trade_kind = "card_payment"
                already_linked_operation_ids.add(int(matched_operation.id))
                linked_count += 1
        if linked_count:
            if commit:
                self.db.commit()
            else:
                self.db.flush()
        return linked_count

    def _validate_trade_sequence(self, trades: list[FxTrade]) -> None:
        quantities_by_currency: dict[str, Decimal] = {}
        ordered = sorted(
            trades,
            key=lambda item: (
                str(item.asset_currency or ""),
                item.trade_date.isoformat() if item.trade_date else "",
                # A not-yet-persisted candidate is the newest ledger action
                # for its day.  Sorting ``None`` as zero would place a new
                # linked card-payment sell before an existing same-day buy and
                # reject a valid balance sequence.
                int(item.id) if item.id is not None else 2**63 - 1,
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
            "bank_rate_banks": self._normalize_bank_codes(raw.get("bank_rate_banks")),
        }

    @staticmethod
    def _normalize_bank_codes(value) -> list[str]:
        source = value if isinstance(value, list) else list(DEFAULT_BANK_RATE_BANKS)
        normalized = []
        for item in source:
            code = str(item or "").strip().lower()
            if code in BANK_RATE_PROVIDERS and code not in normalized:
                normalized.append(code)
        return normalized

    def get_bank_rates(
        self,
        *,
        user_id: int,
        currencies: list[str] | None = None,
    ) -> list[dict]:
        prefs = self.get_currency_preferences(user_id)
        bank_codes = list(prefs.get("bank_rate_banks") or [])
        if not bank_codes:
            return []
        target_currencies = []
        for item in currencies or prefs.get("tracked_currencies") or []:
            try:
                code = self._normalize_currency(str(item))
            except ValueError:
                continue
            if code != "BYN" and code not in target_currencies:
                target_currencies.append(code)
        if not target_currencies:
            return []
        rows = self.repo.list_bank_rates(
            bank_codes=bank_codes,
            currencies=target_currencies,
        )
        bank_order = {code: index for index, code in enumerate(bank_codes)}
        currency_order = {code: index for index, code in enumerate(target_currencies)}
        rows.sort(
            key=lambda row: (
                currency_order.get(row.currency, 999),
                bank_order.get(row.bank_code, 999),
            )
        )
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(minutes=BANK_RATE_STALE_MINUTES)
        result = []
        for row in rows:
            fetched_at = row.fetched_at
            aware_fetched_at = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=timezone.utc)
            quoted_at = row.quoted_at
            aware_quoted_at = (
                quoted_at if quoted_at is None or quoted_at.tzinfo else quoted_at.replace(tzinfo=timezone.utc)
            )
            freshness_timestamp = min(
                value for value in (aware_fetched_at, aware_quoted_at) if value is not None
            )
            provider = BANK_RATE_PROVIDERS.get(row.bank_code, {})
            result.append(
                {
                    "bank_code": row.bank_code,
                    "bank_name": row.bank_name,
                    "currency": row.currency,
                    "base_currency": row.base_currency,
                    "scale": int(row.scale or 1),
                    "buy_rate": self._rate(row.buy_rate),
                    "sell_rate": self._rate(row.sell_rate),
                    "channel": row.channel,
                    "channel_label": str(provider.get("channel_label") or row.channel),
                    "location_name": row.location_name,
                    "quoted_at": row.quoted_at,
                    "fetched_at": row.fetched_at,
                    "stale": freshness_timestamp < stale_cutoff,
                }
            )
        return result

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
        allow_linked_operation: bool = False,
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
        if normalized_trade_kind != "manual" and not allow_linked_operation:
            raise ValueError("trade_kind is managed by operations")
        if linked_operation_id is not None and not allow_linked_operation:
            raise ValueError("linked_operation_id is managed by operations")
        if normalized_asset == normalized_quote:
            raise ValueError("asset_currency and quote_currency must differ")
        if normalized_quantity <= 0 or normalized_unit_price <= 0:
            raise ValueError("quantity and unit_price must be positive")

        self.repo.lock_user_currency_ledger(user_id=user_id)
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
        self.activity.record_created(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="currency_trade",
            entity_id=int(item.id),
            title="Валютная сделка создана",
            metadata=ActivityService.snapshot(item, self.TRADE_FIELDS),
            source="system" if normalized_trade_kind == "card_payment" else "web",
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
        commit: bool = True,
    ) -> FxTrade:
        item = self.repo.get_trade(user_id=user_id, trade_id=trade_id)
        if not item:
            raise ValueError("Currency trade not found")
        if getattr(item, "linked_operation_id", None) is not None and not allow_linked_trade_update:
            raise ValueError("Linked settlement trade must be edited from the operation")
        if linked_operation_id is not None and not allow_linked_trade_update:
            raise ValueError("linked_operation_id is managed by operations")
        before_activity = ActivityService.snapshot(item, self.TRADE_FIELDS)
        normalized_side = self._normalize_side(side)
        normalized_asset = self._normalize_currency(asset_currency)
        normalized_quote = self._normalize_currency(quote_currency)
        normalized_quantity = self._qty(quantity)
        normalized_unit_price = self._rate(unit_price)
        normalized_fee = self._money(fee)
        normalized_trade_kind = self._normalize_trade_kind(trade_kind)
        if normalized_trade_kind != "manual" and not allow_linked_trade_update:
            raise ValueError("trade_kind is managed by operations")
        if normalized_asset == normalized_quote:
            raise ValueError("asset_currency and quote_currency must differ")
        if normalized_quantity <= 0 or normalized_unit_price <= 0:
            raise ValueError("quantity and unit_price must be positive")
        self.repo.lock_user_currency_ledger(user_id=user_id)
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
        after_activity = ActivityService.snapshot(item, self.TRADE_FIELDS)
        self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="currency_trade",
            entity_id=int(item.id),
            before=before_activity,
            after=after_activity,
            labels=self.TRADE_LABELS,
            title="Валютная сделка изменена",
            source="system" if normalized_trade_kind == "card_payment" else "web",
        )
        if commit:
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
        else:
            self.db.flush()
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
                commit=commit,
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
            allow_linked_operation=True,
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
        self.repo.lock_user_currency_ledger(user_id=user_id)
        trades = self.repo.list_all_trades(user_id=user_id)
        self._validate_trade_sequence([trade for trade in trades if trade.id != item.id])
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="currency_trade",
            entity_id=int(item.id),
            event_type="deleted",
            title="Валютная сделка удалена",
            metadata=ActivityService.snapshot(item, self.TRADE_FIELDS),
        )
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
        invalidate_plans_cache(user_id)
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
        return self.reporting.compute_positions(user_id=user_id)

    def get_available_balance(
        self,
        *,
        user_id: int,
        currency: str,
        as_of: date,
        exclude_linked_operation_id: int | None = None,
    ) -> dict:
        normalized_currency = self._normalize_currency(currency)
        trades = [
            trade
            for trade in self.repo.list_all_trades(user_id=user_id)
            if self._normalize_currency(trade.asset_currency) == normalized_currency
            and (
                exclude_linked_operation_id is None
                or int(getattr(trade, "linked_operation_id", 0) or 0) != exclude_linked_operation_id
            )
        ]
        balance = Decimal("0")
        for trade in trades:
            if trade.trade_date >= as_of:
                continue
            quantity = self._qty(trade.quantity)
            balance = self._qty(balance + quantity if trade.side == "buy" else balance - quantity)

        # A historical debit must leave every later point non-negative, not only
        # the balance displayed on the operation date.
        available = balance
        for trade in trades:
            if trade.trade_date < as_of:
                continue
            quantity = self._qty(trade.quantity)
            balance = self._qty(balance + quantity if trade.side == "buy" else balance - quantity)
            available = min(available, balance)

        return {
            "currency": normalized_currency,
            "as_of": as_of,
            "available_quantity": self._qty(max(available, Decimal("0"))),
            "current_quantity": self._qty(max(balance, Decimal("0"))),
        }

    def get_overview(self, *, user_id: int, currency: str | None = None, trades_limit: int = 100) -> dict:
        return self.reporting.get_overview(
            user_id=user_id,
            currency=currency,
            trades_limit=trades_limit,
        )

    def list_trades(
        self,
        *,
        user_id: int,
        currency: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        return self.reporting.list_trades(
            user_id=user_id,
            currency=currency,
            page=page,
            page_size=page_size,
        )

    def get_performance_history(
        self,
        *,
        user_id: int,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        return self.reporting.get_performance_history(
            user_id=user_id,
            currency=currency,
            date_from=date_from,
            date_to=date_to,
        )

    def get_rate_history(
        self,
        *,
        user_id: int,
        currency: str,
        limit: int = 120,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        return self.reporting.get_rate_history(
            user_id=user_id,
            currency=currency,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
