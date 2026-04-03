from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import (
    build_operations_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_dashboard_analytics_cache,
    invalidate_dashboard_summary_cache,
    invalidate_item_templates_cache,
    invalidate_operations_cache,
    set_json,
)
from app.core.logging import log_background_job_event
from app.db.models import Category, CategoryGroup
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.repositories.operation_repo import OperationRepository
from app.services.currency_service import CurrencyService
from app.services.operation_item_template_service import OperationItemTemplateService


MONEY_Q = Decimal("0.01")
QTY_Q = Decimal("0.001")
RATE_Q = Decimal("0.000001")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class OperationService:
    LARGE_OPERATION_THRESHOLD = Decimal("100")

    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)
        self.currency_repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.item_templates = OperationItemTemplateService(db, self.repo)

    @classmethod
    def _resolve_quick_view_filters(cls, quick_view: str | None) -> dict:
        view = (quick_view or "all").strip()
        if view == "receipt":
            return {"receipt_only": True, "uncategorized_only": False, "min_amount": None}
        if view == "large":
            return {"receipt_only": False, "uncategorized_only": False, "min_amount": cls.LARGE_OPERATION_THRESHOLD}
        if view == "uncategorized":
            return {"receipt_only": False, "uncategorized_only": True, "min_amount": None}
        return {"receipt_only": False, "uncategorized_only": False, "min_amount": None}

    @staticmethod
    def _normalize_quick_view_cache_token(quick_view_filters: dict) -> str:
        if quick_view_filters["receipt_only"]:
            return "receipt"
        if quick_view_filters["uncategorized_only"]:
            return "uncategorized"
        if quick_view_filters["min_amount"] is not None:
            return "large"
        return "all"

    @staticmethod
    def _normalize_currency_scope(currency_scope: str | None) -> str:
        scope = str(currency_scope or "all").strip().lower()
        if scope not in {"all", "base", "foreign"}:
            raise ValueError("currency_scope must be one of: all, base, foreign")
        return scope

    def create_operation(
        self,
        user_id: int,
        kind: str,
        amount: Decimal | None,
        operation_date: date,
        category_id: int | None,
        note: str | None,
        currency: str | None = None,
        fx_rate: Decimal | None = None,
        receipt_items: list[dict] | None = None,
        fx_settlement: dict | None = None,
    ):
        self._validate_kind(kind)
        normalized_items, receipt_total = self._normalize_receipt_items(receipt_items or [])
        category_id = self._resolve_effective_operation_category_id(
            category_id=category_id,
            receipt_items=normalized_items,
        )
        original_amount = self._resolve_operation_amount(amount=amount, receipt_total=receipt_total)
        base_currency = self._get_user_base_currency(user_id)
        normalized_currency, normalized_fx_rate, base_amount = self._resolve_currency_amounts(
            user_id=user_id,
            original_amount=original_amount,
            currency=currency,
            fx_rate=fx_rate,
            base_currency=base_currency,
        )

        item = self.repo.create(
            user_id,
            kind,
            base_amount,
            original_amount,
            normalized_currency,
            base_currency,
            normalized_fx_rate,
            operation_date,
            category_id,
            note,
        )
        if fx_settlement:
            normalized_settlement = self._normalize_fx_settlement(
                user_id=user_id,
                kind=kind,
                operation_amount=base_amount,
                operation_date=operation_date,
                base_currency=base_currency,
                payload=fx_settlement,
            )
            currency_service = CurrencyService(self.db)
            currency_service.sync_linked_operation_trade(
                user_id=user_id,
                operation_id=item.id,
                asset_currency=normalized_settlement["asset_currency"],
                quote_currency=base_currency,
                quantity=normalized_settlement["quantity"],
                unit_price=normalized_settlement["unit_price"],
                trade_date=operation_date,
                note=normalized_settlement["note"],
                commit=False,
            )
        if normalized_items:
            storage_items = self.item_templates.resolve_templates_and_prices(
                user_id=user_id,
                operation_id=item.id,
                operation_date=operation_date,
                category_id=category_id,
                normalized_items=normalized_items,
            )
            self.repo.replace_receipt_items(user_id=user_id, operation_id=item.id, items=storage_items)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        self.db.refresh(item)
        log_background_job_event(
            "operation_service",
            "operation_created",
            user_id=user_id,
            operation_id=item.id,
            kind=item.kind,
            category_id=item.category_id,
            currency=item.currency,
            has_receipt=bool(normalized_items),
            has_fx_settlement=bool(fx_settlement),
        )
        return self._serialize_operation(user_id=user_id, operation=item)

    def list_operations(
        self,
        user_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        quick_view: str | None = None,
        currency_scope: str | None = None,
    ) -> tuple[list, int]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if kind:
            self._validate_kind(kind)
        normalized_currency_scope = self._normalize_currency_scope(currency_scope)
        base_currency = self._get_user_base_currency(user_id)
        quick_view_filters = self._resolve_quick_view_filters(quick_view)
        quick_view_token = self._normalize_quick_view_cache_token(quick_view_filters)
        cache_key = build_operations_cache_key(
            user_id=user_id,
            view="list",
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            quick_view=quick_view_token,
            currency_scope=normalized_currency_scope,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"], int(cached["total"])

        items, total = self.repo.list_filtered(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            receipt_only=quick_view_filters["receipt_only"],
            uncategorized_only=quick_view_filters["uncategorized_only"],
            min_amount=quick_view_filters["min_amount"],
            currency_scope=normalized_currency_scope,
            base_currency=base_currency,
        )
        operation_ids = [int(item.id) for item in items]
        receipt_by_operation = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=operation_ids,
        )
        result = [
            self._serialize_operation(
                user_id=user_id,
                operation=item,
                receipt_items=receipt_by_operation.get(int(item.id), []),
            )
            for item in items
        ]
        set_json(
            cache_key,
            {"items": result, "total": total},
            ttl_seconds=get_namespace_ttl_seconds("operations"),
        )
        return result, total

    def summarize_operations(
        self,
        *,
        user_id: int,
        kind: str | None,
        date_from: date | None,
        date_to: date | None,
        category_id: int | None,
        q: str | None,
        quick_view: str | None = None,
        currency_scope: str | None = None,
    ) -> dict:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if kind:
            self._validate_kind(kind)
        normalized_currency_scope = self._normalize_currency_scope(currency_scope)
        base_currency = self._get_user_base_currency(user_id)
        quick_view_filters = self._resolve_quick_view_filters(quick_view)
        quick_view_token = self._normalize_quick_view_cache_token(quick_view_filters)
        cache_key = build_operations_cache_key(
            user_id=user_id,
            view="summary",
            page=None,
            page_size=None,
            sort_by=None,
            sort_dir=None,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            quick_view=quick_view_token,
            currency_scope=normalized_currency_scope,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached
        income_total, expense_total, total = self.repo.summary_filtered(
            user_id=user_id,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            receipt_only=quick_view_filters["receipt_only"],
            uncategorized_only=quick_view_filters["uncategorized_only"],
            min_amount=quick_view_filters["min_amount"],
            currency_scope=normalized_currency_scope,
            base_currency=base_currency,
        )
        payload = {
            "income_total": income_total,
            "expense_total": expense_total,
            "balance": income_total - expense_total,
            "total": total,
        }
        set_json(
            cache_key,
            payload,
            ttl_seconds=get_namespace_ttl_seconds("operations"),
        )
        return payload

    @staticmethod
    def _normalize_money_flow_direction(direction: str | None) -> str:
        value = str(direction or "all").strip().lower()
        if value not in {"all", "inflow", "outflow"}:
            raise ValueError("direction must be one of: all, inflow, outflow")
        return value

    @staticmethod
    def _normalize_money_flow_source(source: str | None) -> str:
        value = str(source or "all").strip().lower()
        if value not in {"all", "operation", "debt", "fx"}:
            raise ValueError("source must be one of: all, operation, debt, fx")
        return value

    def _matches_money_flow_query(self, item: dict, q: str | None) -> bool:
        query = " ".join((q or "").strip().split()).casefold()
        if not query:
            return True
        haystack = " ".join([
            str(item.get("title") or ""),
            str(item.get("subtitle") or ""),
            str(item.get("note") or ""),
            str(item.get("category_name") or ""),
            str(item.get("counterparty_name") or ""),
            str(item.get("asset_currency") or ""),
            str(item.get("quote_currency") or ""),
            str(item.get("trade_side") or ""),
            str(item.get("source_kind") or ""),
        ]).casefold()
        return query in haystack

    def _build_money_flow_dataset(
        self,
        *,
        user_id: int,
        sort_by: str,
        sort_dir: str,
        date_from: date | None,
        date_to: date | None,
        q: str | None,
        direction: str | None,
        source: str | None,
        currency_scope: str | None,
    ) -> list[dict]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        normalized_direction = self._normalize_money_flow_direction(direction)
        normalized_source = self._normalize_money_flow_source(source)
        normalized_currency_scope = self._normalize_currency_scope(currency_scope)
        base_currency = self._get_user_base_currency(user_id)
        items: list[dict] = []

        def include_direction(flow_direction: str) -> bool:
            if normalized_direction == "all":
                return True
            return flow_direction == normalized_direction

        def include_currency(event_currency: str, event_base_currency: str) -> bool:
            currency = str(event_currency or event_base_currency or base_currency).upper()
            base = str(event_base_currency or base_currency).upper()
            if normalized_currency_scope == "all":
                return True
            if normalized_currency_scope == "base":
                return currency == base
            return currency != base

        def include_event_date(event_date) -> bool:
            if isinstance(event_date, str):
                try:
                    event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                except ValueError:
                    return False
            if event_date is None:
                return False
            if date_from and event_date < date_from:
                return False
            if date_to and event_date > date_to:
                return False
            return True

        if normalized_source in {"all", "operation"}:
            operation_kind = None
            if normalized_direction == "inflow":
                operation_kind = "income"
            elif normalized_direction == "outflow":
                operation_kind = "expense"
            operations = self.repo.list_filtered_all(
                user_id=user_id,
                sort_by=sort_by,
                sort_dir=sort_dir,
                kind=operation_kind,
                date_from=date_from,
                date_to=date_to,
                category_id=None,
                q=q,
                receipt_only=False,
                uncategorized_only=False,
                min_amount=None,
                currency_scope=normalized_currency_scope,
                base_currency=base_currency,
            )
            receipt_by_operation = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(item.id) for item in operations],
            )
            for operation in operations:
                payload = self._serialize_operation(
                    user_id=user_id,
                    operation=operation,
                    receipt_items=receipt_by_operation.get(int(operation.id), []),
                )
                flow_direction = "inflow" if payload["kind"] == "income" else "outflow"
                item = {
                    "id": f"operation:{payload['id']}",
                    "source_kind": "operation",
                    "source_id": int(payload["id"]),
                    "flow_direction": flow_direction,
                    "event_date": payload["operation_date"],
                    "amount": payload["amount"],
                    "original_amount": payload["original_amount"],
                    "currency": payload["currency"],
                    "base_currency": payload["base_currency"],
                    "fx_rate": payload["fx_rate"],
                    "title": payload.get("category_name") or "Без категории",
                    "subtitle": "Обычная операция",
                    "note": payload.get("note"),
                    "category_id": payload.get("category_id"),
                    "category_name": payload.get("category_name"),
                    "category_icon": payload.get("category_icon"),
                    "category_accent_color": payload.get("category_accent_color"),
                    "has_fx_settlement": bool(payload.get("fx_settlement")),
                    "settlement_asset_currency": (
                        str(payload.get("fx_settlement", {}).get("asset_currency") or "").upper()
                        if isinstance(payload.get("fx_settlement"), dict)
                        else None
                    ),
                    "receipt_items": payload.get("receipt_items") or [],
                    "receipt_total": payload.get("receipt_total"),
                    "receipt_discrepancy": payload.get("receipt_discrepancy"),
                    "can_open_source": False,
                    "open_section": "operations",
                    "open_label": "Операция",
                }
                if self._matches_money_flow_query(item, q):
                    items.append(item)

        if normalized_source in {"all", "debt"}:
            from app.services.debt_service import DebtService

            debt_service = DebtService(self.db)
            for card in debt_service.list_cards(user_id=user_id, include_closed=True, q=None):
                for debt in card.get("debts", []) or []:
                    debt_currency = str(debt.get("currency") or base_currency).upper()
                    debt_base_currency = str(debt.get("base_currency") or base_currency).upper()
                    if not include_currency(debt_currency, debt_base_currency):
                        continue
                    direction_sign = -1 if str(debt.get("direction") or "lend") == "lend" else 1
                    for issuance in debt.get("issuances", []) or []:
                        event_date = issuance.get("issuance_date")
                        if not include_event_date(event_date):
                            continue
                        flow_direction = "outflow" if direction_sign < 0 else "inflow"
                        if not include_direction(flow_direction):
                            continue
                        is_lend = direction_sign < 0
                        item = {
                            "id": f"debt-issuance:{issuance['id']}",
                            "source_kind": "debt",
                            "source_id": int(debt["id"]),
                            "flow_direction": flow_direction,
                            "event_date": event_date,
                            "amount": self._money(issuance.get("current_base_amount") or issuance.get("amount") or 0),
                            "original_amount": self._money(issuance.get("amount") or 0),
                            "currency": debt_currency,
                            "base_currency": debt_base_currency,
                            "fx_rate": self._rate(Decimal("1")),
                            "title": "Я дал в долг" if is_lend else "Я взял в долг",
                            "subtitle": str(card.get("counterparty") or "Контрагент"),
                            "note": issuance.get("note") or debt.get("note"),
                            "counterparty_id": int(card["counterparty_id"]),
                            "counterparty_name": str(card.get("counterparty") or ""),
                            "can_open_source": True,
                            "open_section": "debts",
                            "open_label": "История долга",
                        }
                        if self._matches_money_flow_query(item, q):
                            items.append(item)
                    for repayment in debt.get("repayments", []) or []:
                        event_date = repayment.get("repayment_date")
                        if not include_event_date(event_date):
                            continue
                        flow_direction = "inflow" if direction_sign < 0 else "outflow"
                        if not include_direction(flow_direction):
                            continue
                        is_lend = direction_sign < 0
                        item = {
                            "id": f"debt-repayment:{repayment['id']}",
                            "source_kind": "debt",
                            "source_id": int(debt["id"]),
                            "flow_direction": flow_direction,
                            "event_date": event_date,
                            "amount": self._money(repayment.get("current_base_amount") or repayment.get("amount") or 0),
                            "original_amount": self._money(repayment.get("amount") or 0),
                            "currency": debt_currency,
                            "base_currency": debt_base_currency,
                            "fx_rate": self._rate(Decimal("1")),
                            "title": "Мне вернули долг" if is_lend else "Я вернул долг",
                            "subtitle": str(card.get("counterparty") or "Контрагент"),
                            "note": repayment.get("note") or debt.get("note"),
                            "counterparty_id": int(card["counterparty_id"]),
                            "counterparty_name": str(card.get("counterparty") or ""),
                            "can_open_source": True,
                            "open_section": "debts",
                            "open_label": "История долга",
                        }
                        if self._matches_money_flow_query(item, q):
                            items.append(item)

        if normalized_source in {"all", "fx"}:
            from app.repositories.currency_repo import CurrencyRepository

            currency_repo = CurrencyRepository(self.db)
            for trade in currency_repo.list_trades_for_period(
                user_id=user_id,
                date_from=date_from or date.min,
                date_to=date_to or date.max,
            ):
                if not CurrencyService.is_cashflow_trade(trade):
                    continue
                quote_currency = str(getattr(trade, "quote_currency", base_currency) or base_currency).upper()
                if quote_currency != base_currency:
                    continue
                flow_direction = "outflow" if trade.side == "buy" else "inflow"
                if not include_direction(flow_direction):
                    continue
                if normalized_currency_scope == "foreign":
                    continue
                gross = Decimal(getattr(trade, "quantity", 0) or 0) * Decimal(getattr(trade, "unit_price", 0) or 0)
                fee = Decimal(getattr(trade, "fee", 0) or 0)
                amount = self._money(gross + fee if trade.side == "buy" else gross - fee)
                item = {
                    "id": f"fx:{trade.id}",
                    "source_kind": "fx",
                    "source_id": int(trade.id),
                    "flow_direction": flow_direction,
                    "event_date": trade.trade_date,
                    "amount": amount,
                    "original_amount": amount,
                    "currency": quote_currency,
                    "base_currency": base_currency,
                    "fx_rate": self._rate(Decimal("1")),
                    "title": f"{'Покупка' if trade.side == 'buy' else 'Продажа'} {str(trade.asset_currency).upper()}",
                    "subtitle": f"{'За' if trade.side == 'buy' else 'В'} {quote_currency} · курс {self._rate(Decimal(trade.unit_price))}",
                    "note": trade.note,
                    "asset_currency": str(trade.asset_currency).upper(),
                    "asset_quantity": self._qty(Decimal(getattr(trade, "quantity", 0) or 0)),
                    "quote_currency": quote_currency,
                    "trade_side": str(trade.side),
                    "can_open_source": True,
                    "open_section": "currency",
                    "open_label": "Редактировать",
                }
                if self._matches_money_flow_query(item, q):
                    items.append(item)

        def sort_key(item: dict):
            if sort_by == "amount":
                primary = Decimal(item.get("amount") or 0)
            elif sort_by == "created_at":
                primary = item.get("source_id") or 0
            else:
                primary = str(item.get("event_date") or "")
            return primary

        reverse = sort_dir != "asc"
        items.sort(
            key=lambda item: (
                sort_key(item),
                str(item.get("event_date") or ""),
                str(item.get("id") or ""),
            ),
            reverse=reverse,
        )
        return items

    def list_money_flow(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
        date_from: date | None,
        date_to: date | None,
        q: str | None,
        direction: str | None = None,
        source: str | None = None,
        currency_scope: str | None = None,
    ) -> tuple[list[dict], int]:
        items = self._build_money_flow_dataset(
            user_id=user_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
        )
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return items[start:end], total

    def summarize_money_flow(
        self,
        *,
        user_id: int,
        date_from: date | None,
        date_to: date | None,
        q: str | None,
        direction: str | None = None,
        source: str | None = None,
        currency_scope: str | None = None,
    ) -> dict:
        items = self._build_money_flow_dataset(
            user_id=user_id,
            sort_by="operation_date",
            sort_dir="desc",
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
        )
        income_total = sum(
            (Decimal(item["amount"]) for item in items if item.get("flow_direction") == "inflow"),
            start=Decimal("0"),
        )
        expense_total = sum(
            (Decimal(item["amount"]) for item in items if item.get("flow_direction") == "outflow"),
            start=Decimal("0"),
        )
        return {
            "income_total": self._money(income_total),
            "expense_total": self._money(expense_total),
            "balance": self._money(income_total - expense_total),
            "total": len(items),
        }

    def _normalize_fx_settlement(
        self,
        *,
        user_id: int,
        kind: str,
        operation_amount: Decimal,
        operation_date: date,
        base_currency: str,
        payload: dict,
    ) -> dict:
        if kind != "expense":
            raise ValueError("fx_settlement is supported only for expense operations")
        asset_currency = str(payload.get("asset_currency") or "").strip().upper()
        quote_total = self._money(payload.get("quote_total") or 0)
        quantity = Decimal(payload.get("quantity") or 0).quantize(QTY_Q)
        unit_price = Decimal(payload.get("unit_price") or 0).quantize(RATE_Q)
        note = str(payload.get("note") or "").strip() or None
        if not _CURRENCY_RE.match(asset_currency):
            raise ValueError("fx_settlement asset_currency must be a 3-letter ISO code")
        if asset_currency == base_currency:
            raise ValueError("fx_settlement asset_currency must differ from base currency")
        if quantity <= 0 or unit_price <= 0 or quote_total <= 0:
            raise ValueError("fx_settlement quantity, quote_total and unit_price must be positive")
        computed_total = self._money(quantity * unit_price)
        if computed_total != quote_total:
            raise ValueError("fx_settlement quote_total must match quantity * unit_price")
        if quote_total != self._money(operation_amount):
            raise ValueError("fx_settlement quote_total must match operation amount in base currency")
        return {
            "asset_currency": asset_currency,
            "quantity": quantity,
            "unit_price": unit_price,
            "quote_total": quote_total,
            "note": note,
            "trade_date": operation_date,
        }

    def get_operation(self, user_id: int, operation_id: int):
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")
        return self._serialize_operation(user_id=user_id, operation=item)

    @staticmethod
    def _resolve_effective_operation_category_id(
        *,
        category_id: int | None,
        receipt_items: list[dict] | None,
    ) -> int | None:
        explicit_category_id = int(category_id or 0)
        if explicit_category_id > 0:
            return explicit_category_id
        unique_receipt_category_ids = {
            int(row.get("category_id") or 0)
            for row in (receipt_items or [])
            if int(row.get("category_id") or 0) > 0
        }
        if len(unique_receipt_category_ids) == 1:
            return next(iter(unique_receipt_category_ids))
        return None

    def update_operation(self, user_id: int, operation_id: int, updates: dict):
        logged_fields = sorted(updates.keys())
        if "kind" in updates and updates["kind"] is not None:
            self._validate_kind(updates["kind"])

        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        receipt_items_input = updates.pop("receipt_items", None) if "receipt_items" in updates else None
        fx_settlement_input = updates.pop("fx_settlement", None) if "fx_settlement" in updates else None
        normalized_items: list[dict] | None = None
        receipt_total: Decimal | None = None
        if receipt_items_input is not None:
            normalized_items, receipt_total = self._normalize_receipt_items(receipt_items_input)
            current_category_id = updates.get("category_id", getattr(item, "category_id", None))
            updates["category_id"] = self._resolve_effective_operation_category_id(
                category_id=current_category_id,
                receipt_items=normalized_items,
            )

        if "amount" in updates:
            if updates["amount"] is None:
                if receipt_items_input is None:
                    raise ValueError("amount must not be null")
                updates["amount"] = self._resolve_operation_amount(amount=None, receipt_total=receipt_total)
            else:
                updates["amount"] = self._money(updates["amount"])

        needs_currency_recalc = any(key in updates for key in ("amount", "currency", "fx_rate"))
        if needs_currency_recalc:
            base_currency = self._get_user_base_currency(user_id)
            current_original_amount = updates.get("amount", self._money(getattr(item, "original_amount", item.amount)))
            current_currency = updates.get("currency", getattr(item, "currency", base_currency))
            current_fx_rate = updates.get("fx_rate", getattr(item, "fx_rate", Decimal("1.000000")))
            normalized_currency, normalized_fx_rate, base_amount = self._resolve_currency_amounts(
                user_id=user_id,
                original_amount=current_original_amount,
                currency=current_currency,
                fx_rate=current_fx_rate,
                base_currency=base_currency,
            )
            updates["original_amount"] = self._money(current_original_amount)
            updates["currency"] = normalized_currency
            updates["base_currency"] = base_currency
            updates["fx_rate"] = normalized_fx_rate
            updates["amount"] = base_amount

        item = self.repo.update(item, updates)

        if normalized_items is not None:
            storage_items: list[dict] = []
            if normalized_items:
                storage_items = self.item_templates.resolve_templates_and_prices(
                    user_id=user_id,
                    operation_id=item.id,
                    operation_date=item.operation_date,
                    category_id=item.category_id,
                    normalized_items=normalized_items,
                )
            self.repo.replace_receipt_items(user_id=user_id, operation_id=item.id, items=storage_items)
            if receipt_total is not None and "amount" not in updates:
                # Keep operation amount as source of truth; discrepancy is reported in output.
                _ = receipt_total

        if "fx_settlement" in logged_fields:
            linked_trade = self.currency_repo.get_trade_by_linked_operation_id(user_id=user_id, operation_id=item.id)
            if fx_settlement_input is None:
                if linked_trade is not None:
                    self.currency_repo.delete_trade(linked_trade)
            else:
                current_kind = str(getattr(item, "kind", updates.get("kind") or "expense"))
                current_base_amount = self._money(getattr(item, "amount", 0))
                current_base_currency = str(getattr(item, "base_currency", self._get_user_base_currency(user_id)) or self._get_user_base_currency(user_id)).upper()
                normalized_settlement = self._normalize_fx_settlement(
                    user_id=user_id,
                    kind=current_kind,
                    operation_amount=current_base_amount,
                    operation_date=item.operation_date,
                    base_currency=current_base_currency,
                    payload=fx_settlement_input,
                )
                currency_service = CurrencyService(self.db)
                currency_service.sync_linked_operation_trade(
                    user_id=user_id,
                    operation_id=item.id,
                    asset_currency=normalized_settlement["asset_currency"],
                    quote_currency=current_base_currency,
                    quantity=normalized_settlement["quantity"],
                    unit_price=normalized_settlement["unit_price"],
                    trade_date=item.operation_date,
                    note=normalized_settlement["note"],
                    commit=False,
                )

        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        self.db.refresh(item)
        log_background_job_event(
            "operation_service",
            "operation_updated",
            user_id=user_id,
            operation_id=item.id,
            kind=item.kind,
            category_id=item.category_id,
            currency=item.currency,
            fields_changed=",".join(logged_fields),
            receipt_updated=normalized_items is not None,
            fx_settlement_updated="fx_settlement" in logged_fields,
        )
        return self._serialize_operation(user_id=user_id, operation=item)

    def delete_operation(self, user_id: int, operation_id: int) -> None:
        item = self.repo.get_by_id(user_id=user_id, operation_id=operation_id)
        if not item:
            raise LookupError("Operation not found")

        self.repo.delete(item)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        log_background_job_event(
            "operation_service",
            "operation_deleted",
            user_id=user_id,
            operation_id=operation_id,
            kind=item.kind,
            category_id=item.category_id,
            currency=getattr(item, "currency", "BYN"),
        )

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
    ) -> tuple[list[dict], int]:
        return self.item_templates.list_item_templates(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
        )

    def list_item_template_prices(
        self,
        *,
        user_id: int,
        template_id: int,
        limit: int = 200,
    ) -> list[dict]:
        return self.item_templates.list_item_template_prices(
            user_id=user_id,
            template_id=template_id,
            limit=limit,
        )

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        name: str,
        latest_unit_price: Decimal | None,
        latest_price_date: date | None = None,
    ) -> dict:
        return self.item_templates.create_item_template(
            user_id=user_id,
            shop_name=shop_name,
            name=name,
            latest_unit_price=latest_unit_price,
            latest_price_date=latest_price_date,
        )

    def update_item_template(
        self,
        *,
        user_id: int,
        template_id: int,
        updates: dict,
    ) -> dict:
        return self.item_templates.update_item_template(
            user_id=user_id,
            template_id=template_id,
            updates=updates,
        )

    def delete_item_template(self, *, user_id: int, template_id: int) -> None:
        self.item_templates.delete_item_template(user_id=user_id, template_id=template_id)

    def delete_all_item_templates(self, *, user_id: int) -> int:
        return self.item_templates.delete_all_item_templates(user_id=user_id)

    def _serialize_operation(self, *, user_id: int, operation, receipt_items: list | None = None) -> dict:
        loaded_items = receipt_items
        if loaded_items is None:
            loaded = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(operation.id)],
            )
            loaded_items = loaded.get(int(operation.id), [])
        category_meta_map = self._get_category_meta_map([row.category_id for row in loaded_items or []] + [operation.category_id])
        receipt_payload = []
        receipt_total = Decimal("0")
        for row in loaded_items or []:
            line_total = self._money(row.line_total)
            receipt_total += line_total
            category_meta = category_meta_map.get(int(row.category_id or 0), {})
            receipt_payload.append(
                {
                    "id": int(row.id),
                    "template_id": row.template_id,
                    "category_id": row.category_id,
                    "category_name": category_meta.get("name"),
                    "category_icon": category_meta.get("icon"),
                    "category_accent_color": category_meta.get("accent_color"),
                    "shop_name": row.shop_name,
                    "name": row.name,
                    "quantity": self._qty(row.quantity),
                    "unit_price": self._money(row.unit_price),
                    "line_total": line_total,
                    "note": row.note,
                }
            )
        amount = self._money(operation.amount)
        original_amount = self._money(getattr(operation, "original_amount", operation.amount))
        currency = str(getattr(operation, "currency", "BYN") or "BYN").upper()
        base_currency = str(getattr(operation, "base_currency", "BYN") or "BYN").upper()
        fx_rate = self._rate(getattr(operation, "fx_rate", Decimal("1.000000")))
        receipt_total_value = self._money(receipt_total) if receipt_payload else None
        discrepancy = self._money(amount - receipt_total) if receipt_payload else None
        linked_trade = self.currency_repo.get_trade_by_linked_operation_id(
            user_id=user_id,
            operation_id=int(operation.id),
        )
        fx_settlement = None
        if linked_trade is not None:
            fx_settlement = {
                "trade_id": int(linked_trade.id),
                "asset_currency": str(linked_trade.asset_currency or "").upper(),
                "quote_currency": str(linked_trade.quote_currency or "").upper(),
                "quantity": self._qty(linked_trade.quantity),
                "quote_total": self._money(Decimal(linked_trade.quantity or 0) * Decimal(linked_trade.unit_price or 0)),
                "unit_price": self._rate(linked_trade.unit_price),
                "trade_date": linked_trade.trade_date,
                "note": linked_trade.note,
            }
        effective_operation_category_id = self._resolve_effective_operation_category_id(
            category_id=getattr(operation, "category_id", None),
            receipt_items=receipt_payload,
        )
        operation_category_meta = category_meta_map.get(int(effective_operation_category_id or 0), {})
        return {
            "id": int(operation.id),
            "kind": operation.kind,
            "amount": amount,
            "original_amount": original_amount,
            "currency": currency,
            "base_currency": base_currency,
            "fx_rate": fx_rate,
            "operation_date": operation.operation_date,
            "category_id": effective_operation_category_id,
            "category_name": operation_category_meta.get("name"),
            "category_icon": operation_category_meta.get("icon"),
            "category_accent_color": operation_category_meta.get("accent_color"),
            "note": operation.note,
            "receipt_items": receipt_payload,
            "receipt_total": receipt_total_value,
            "receipt_discrepancy": discrepancy,
            "fx_settlement": fx_settlement,
        }

    def _normalize_currency(self, value: str | None, default: str = "BYN") -> str:
        code = str(value or default).strip().upper()
        if not _CURRENCY_RE.match(code):
            raise ValueError("Currency must be a 3-letter ISO code")
        return code

    def _rate(self, value: Decimal | None) -> Decimal:
        return Decimal(value or 0).quantize(RATE_Q)

    def _get_user_base_currency(self, user_id: int) -> str:
        prefs = self.preferences.get_or_create(user_id)
        ui_prefs = prefs.data.get("ui") if isinstance(prefs.data.get("ui"), dict) else {}
        return self._normalize_currency(ui_prefs.get("currency") or "BYN")

    def _resolve_currency_amounts(
        self,
        *,
        user_id: int,
        original_amount: Decimal,
        currency: str | None,
        fx_rate: Decimal | None,
        base_currency: str,
    ) -> tuple[str, Decimal, Decimal]:
        _ = user_id
        normalized_currency = self._normalize_currency(currency or base_currency, default=base_currency)
        normalized_original_amount = self._money(original_amount)
        if normalized_currency == base_currency:
            normalized_fx_rate = self._rate(Decimal("1"))
            return normalized_currency, normalized_fx_rate, normalized_original_amount
        normalized_fx_rate = self._rate(fx_rate)
        if normalized_fx_rate <= 0:
            raise ValueError("fx_rate must be positive for non-base currency operations")
        base_amount = self._money(Decimal(normalized_original_amount) * Decimal(normalized_fx_rate))
        return normalized_currency, normalized_fx_rate, base_amount

    def _get_category_meta_map(self, category_ids: list[int | None]) -> dict[int, dict]:
        normalized_ids = sorted({int(category_id) for category_id in category_ids if int(category_id or 0) > 0})
        if not normalized_ids:
            return {}
        stmt = (
            select(Category, CategoryGroup)
            .outerjoin(CategoryGroup, CategoryGroup.id == Category.group_id)
            .where(Category.id.in_(normalized_ids))
        )
        result: dict[int, dict] = {}
        for category, group in self.db.execute(stmt).all():
            result[int(category.id)] = {
                "name": category.name,
                "icon": category.icon or (group.icon if group else None),
                "accent_color": group.accent_color if group else None,
            }
        return result

    def _normalize_receipt_items(self, receipt_items: list[dict]) -> tuple[list[dict], Decimal | None]:
        normalized: list[dict] = []
        receipt_total = Decimal("0")
        for item in receipt_items:
            shop_name_raw = " ".join(str(item.get("shop_name") or "").split())
            shop_name = shop_name_raw or None
            name = " ".join(str(item.get("name") or "").split())
            if not name:
                raise ValueError("receipt item name must not be empty")
            quantity = self._qty(item.get("quantity") or Decimal("0"))
            if quantity <= 0:
                raise ValueError("receipt item quantity must be greater than 0")
            unit_price = self._money(item.get("unit_price") or Decimal("0"))
            if unit_price <= 0:
                raise ValueError("receipt item unit_price must be greater than 0")
            line_total = self._money(quantity * unit_price)
            note = item.get("note")
            normalized.append(
                {
                    "category_id": item.get("category_id"),
                    "shop_name": shop_name,
                    "name": name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "note": note,
                }
            )
            receipt_total += line_total
        if not normalized:
            return normalized, None
        return normalized, self._money(receipt_total)

    def _resolve_operation_amount(self, *, amount: Decimal | None, receipt_total: Decimal | None) -> Decimal:
        if amount is None and receipt_total is None:
            raise ValueError("amount is required when receipt_items are empty")
        if amount is None and receipt_total is not None:
            return self._money(receipt_total)
        if amount is None:
            raise ValueError("amount is required")
        return self._money(amount)

    @staticmethod
    def _validate_kind(kind: str) -> None:
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be either 'income' or 'expense'")

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value).quantize(MONEY_Q, rounding=ROUND_HALF_UP)

    @staticmethod
    def _qty(value) -> Decimal:
        return Decimal(value).quantize(QTY_Q, rounding=ROUND_HALF_UP)
