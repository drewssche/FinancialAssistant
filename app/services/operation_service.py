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
    invalidate_plans_cache,
    set_json,
)
from app.core.logging import log_background_job_event
from app.db.models import Category, CategoryGroup, FxTrade, OperationItemTemplate
from app.repositories.currency_repo import CurrencyRepository
from app.repositories.preference_repo import PreferenceRepository
from app.repositories.operation_repo import OperationRepository
from app.services.activity_service import ActivityService
from app.services.bank_currency_rate_registry import display_scale
from app.services.currency_service import CurrencyService
from app.services.fx_rate_policy_service import FxRatePolicyService
from app.services.operation_item_template_service import OperationItemTemplateService
from app.services.operation_money_flow_service import OperationMoneyFlowService


MONEY_Q = Decimal("0.01")
QTY_Q = Decimal("0.001")
RATE_Q = Decimal("0.000001")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class OperationService:
    LARGE_OPERATION_THRESHOLD = Decimal("100")
    ACTIVITY_FIELDS = [
        "kind",
        "original_amount",
        "currency",
        "fx_rate",
        "fx_rate_source",
        "fx_bank_code",
        "fx_bank_channel",
        "fx_rate_kind",
        "fx_payment_mode",
        "operation_date",
        "category_id",
        "note",
    ]
    ACTIVITY_LABELS = {
        "kind": "Тип",
        "original_amount": "Сумма",
        "currency": "Валюта",
        "fx_rate": "Курс",
        "fx_rate_source": "Источник курса",
        "fx_bank_code": "Банк",
        "fx_bank_channel": "Канал курса",
        "fx_rate_kind": "Курс банка",
        "fx_payment_mode": "Способ оплаты",
        "operation_date": "Дата",
        "category_id": "Категория",
        "note": "Комментарий",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repo = OperationRepository(db)
        self.currency_repo = CurrencyRepository(db)
        self.preferences = PreferenceRepository(db)
        self.item_templates = OperationItemTemplateService(db, self.repo)
        self.activity = ActivityService(db)
        self.money_flow = OperationMoneyFlowService(self)

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
        fx_rate_source: str | None = None,
        fx_bank_code: str | None = None,
        fx_bank_channel: str | None = None,
        fx_rate_kind: str | None = None,
        fx_manual_rate: Decimal | None = None,
        fx_payment_mode: str | None = None,
        receipt_items: list[dict] | None = None,
        fx_settlement: dict | None = None,
        fx_policy_snapshot: dict | None = None,
        commit: bool = True,
    ):
        self._validate_kind(kind)
        normalized_items, receipt_total = self._normalize_receipt_items(receipt_items or [])
        category_id = self._resolve_effective_operation_category_id(
            category_id=category_id,
            receipt_items=normalized_items,
        )
        original_amount = self._resolve_operation_amount(amount=amount, receipt_total=receipt_total)
        base_currency = self._get_user_base_currency(user_id)
        normalized_currency = self._normalize_currency(currency or base_currency, default=base_currency)
        policy = FxRatePolicyService(self.db)
        explicit_payment_mode = fx_payment_mode is not None
        effective_payment_mode = policy.normalize_payment_mode(fx_payment_mode)
        policy.validate_payment_mode(
            kind=kind,
            currency=normalized_currency,
            base_currency=base_currency,
            payment_mode=effective_payment_mode,
        )
        if normalized_currency == base_currency:
            normalized_fx_rate = self._rate(Decimal("1"))
            rate_snapshot = {
                "fx_rate_source": None,
                "fx_bank_code": None,
                "fx_bank_name": None,
                "fx_bank_channel": None,
                "fx_rate_kind": None,
                "fx_rate_scale": 1,
                "fx_rate_date": None,
                "fx_quoted_at": None,
                "fx_fetched_at": None,
                "fx_rate_stale": False,
                "fx_payment_mode": "valuation",
            }
        elif fx_policy_snapshot is not None:
            normalized_fx_rate = self._rate(fx_policy_snapshot.get("fx_rate"))
            if normalized_fx_rate <= 0:
                raise ValueError("fx policy snapshot rate must be positive")
            rate_snapshot = {
                "fx_rate_source": fx_policy_snapshot.get("fx_rate_source"),
                "fx_bank_code": fx_policy_snapshot.get("fx_bank_code"),
                "fx_bank_name": fx_policy_snapshot.get("fx_bank_name"),
                "fx_bank_channel": fx_policy_snapshot.get("fx_bank_channel"),
                "fx_rate_kind": fx_policy_snapshot.get("fx_rate_kind"),
                "fx_rate_scale": max(1, int(fx_policy_snapshot.get("fx_rate_scale") or 1)),
                "fx_rate_date": fx_policy_snapshot.get("fx_rate_date"),
                "fx_quoted_at": fx_policy_snapshot.get("fx_quoted_at"),
                "fx_fetched_at": fx_policy_snapshot.get("fx_fetched_at"),
                "fx_rate_stale": bool(fx_policy_snapshot.get("fx_rate_stale", False)),
                "fx_payment_mode": effective_payment_mode,
            }
        else:
            effective_source = policy.normalize_source(
                fx_rate_source,
                default="manual" if fx_rate is not None or fx_manual_rate is not None else None,
            )
            if effective_source is None:
                raise ValueError("fx_rate_source or legacy fx_rate is required for non-base currency operations")
            resolution = policy.resolve(
                user_id=user_id,
                currency=normalized_currency,
                base_currency=base_currency,
                source=effective_source,
                bank_code=fx_bank_code,
                bank_channel=fx_bank_channel,
                rate_kind=fx_rate_kind,
                manual_rate=fx_manual_rate,
                legacy_unit_rate=fx_rate,
                as_of=operation_date,
            )
            normalized_fx_rate = resolution.rate
            rate_snapshot = resolution.operation_snapshot(payment_mode=effective_payment_mode)
        base_amount = self._money(Decimal(original_amount) * Decimal(normalized_fx_rate))

        item = self.repo.create(
            user_id=user_id,
            kind=kind,
            amount=base_amount,
            original_amount=original_amount,
            currency=normalized_currency,
            base_currency=base_currency,
            fx_rate=normalized_fx_rate,
            fx_rate_source=rate_snapshot["fx_rate_source"],
            fx_bank_code=rate_snapshot["fx_bank_code"],
            fx_bank_name=rate_snapshot["fx_bank_name"],
            fx_bank_channel=rate_snapshot["fx_bank_channel"],
            fx_rate_kind=rate_snapshot["fx_rate_kind"],
            fx_rate_scale=rate_snapshot["fx_rate_scale"],
            fx_rate_date=rate_snapshot["fx_rate_date"],
            fx_quoted_at=rate_snapshot["fx_quoted_at"],
            fx_fetched_at=rate_snapshot["fx_fetched_at"],
            fx_rate_stale=rate_snapshot["fx_rate_stale"],
            fx_payment_mode=rate_snapshot["fx_payment_mode"],
            operation_date=operation_date,
            category_id=category_id,
            note=note,
        )
        if explicit_payment_mode and effective_payment_mode != "foreign_balance" and fx_settlement:
            raise ValueError(f"{effective_payment_mode} must not create a separate currency trade")
        if effective_payment_mode == "foreign_balance":
            fx_settlement = {
                "asset_currency": normalized_currency,
                "quantity": original_amount,
                "quote_total": base_amount,
                "unit_price": normalized_fx_rate,
                "note": (fx_settlement or {}).get("note") if isinstance(fx_settlement, dict) else None,
            }
        if fx_settlement:
            try:
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
            except Exception:
                self.db.rollback()
                raise
        if normalized_items:
            storage_items = self.item_templates.resolve_templates_and_prices(
                user_id=user_id,
                operation_id=item.id,
                operation_date=operation_date,
                category_id=category_id,
                normalized_items=normalized_items,
            )
            self.repo.replace_receipt_items(user_id=user_id, operation_id=item.id, items=storage_items)
        self.activity.record_created(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="operation",
            entity_id=int(item.id),
            title="Операция создана",
            metadata={
                "kind": item.kind,
                "amount": str(item.original_amount),
                "currency": item.currency,
                "has_receipt": bool(normalized_items),
                "has_fx_settlement": bool(fx_settlement),
            },
        )
        if commit:
            self.db.commit()
            self._invalidate_caches(user_id)
            self.db.refresh(item)
        else:
            self.db.flush()
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

    @staticmethod
    def _invalidate_caches(user_id: int) -> None:
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        invalidate_plans_cache(user_id)

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
        brand_id: int | None = None,
        product_id: int | None = None,
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
            brand_id=brand_id,
            product_id=product_id,
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
            brand_id=brand_id,
            product_id=product_id,
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
        brand_meta_map = self._get_brand_meta_map(
            user_id=user_id,
            template_ids=[
                row.template_id
                for rows in receipt_by_operation.values()
                for row in rows
            ],
        )
        result = [
            self._serialize_operation(
                user_id=user_id,
                operation=item,
                receipt_items=receipt_by_operation.get(int(item.id), []),
                brand_meta_map=brand_meta_map,
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
        brand_id: int | None = None,
        product_id: int | None = None,
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
            brand_id=brand_id,
            product_id=product_id,
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
            brand_id=brand_id,
            product_id=product_id,
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
        category_id: int | None = None,
        item_template_id: int | None = None,
        product_id: int | None = None,
        brand_id: int | None = None,
    ) -> tuple[list[dict], int]:
        return self.money_flow.list(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
            category_id=category_id,
            item_template_id=item_template_id,
            product_id=product_id,
            brand_id=brand_id,
        )

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
        category_id: int | None = None,
        item_template_id: int | None = None,
        product_id: int | None = None,
        brand_id: int | None = None,
    ) -> dict:
        return self.money_flow.summarize(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
            category_id=category_id,
            item_template_id=item_template_id,
            product_id=product_id,
            brand_id=brand_id,
        )

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
        if (
            updates.get("kind") is not None
            and updates["kind"] != "income"
            and self.repo.has_work_payment_link(user_id=user_id, operation_id=operation_id)
        ):
            raise ValueError("Сначала отвяжите операцию от выплаты, затем измените её тип")
        before_activity = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)

        receipt_items_input = updates.pop("receipt_items", None) if "receipt_items" in updates else None
        fx_settlement_input = updates.pop("fx_settlement", None) if "fx_settlement" in updates else None
        fx_manual_rate_present = "fx_manual_rate" in updates
        fx_manual_rate = updates.pop("fx_manual_rate", None) if fx_manual_rate_present else None
        fx_refresh_rate = bool(updates.pop("fx_refresh_rate", False))
        normalized_items: list[dict] | None = None
        before_receipt_items: list | None = None
        receipt_changes: dict | None = None
        receipt_total: Decimal | None = None
        if receipt_items_input is not None:
            before_receipt_items = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(item.id)],
            ).get(int(item.id), [])
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
                updates["amount"] = self._resolve_operation_amount(amount=updates["amount"], receipt_total=None)

        policy = FxRatePolicyService(self.db)
        base_currency = self._get_user_base_currency(user_id)
        current_currency = self._normalize_currency(getattr(item, "currency", base_currency), default=base_currency)
        normalized_currency = self._normalize_currency(
            updates.get("currency", current_currency),
            default=base_currency,
        )
        currency_changed = normalized_currency != current_currency
        current_source = policy.normalize_source(getattr(item, "fx_rate_source", None))
        requested_source = (
            policy.normalize_source(updates.get("fx_rate_source"))
            if "fx_rate_source" in updates
            else current_source
        )
        current_bank_code = policy.normalize_bank_code(getattr(item, "fx_bank_code", None))
        requested_bank_code = (
            policy.normalize_bank_code(updates.get("fx_bank_code"))
            if "fx_bank_code" in updates
            else current_bank_code
        )
        current_bank_channel = str(getattr(item, "fx_bank_channel", None) or "").strip().lower() or None
        requested_bank_channel = (
            policy.normalize_bank_channel(bank_code=requested_bank_code, value=updates.get("fx_bank_channel"))
            if "fx_bank_channel" in updates or requested_bank_code != current_bank_code
            else current_bank_channel
        )
        current_rate_kind = policy.normalize_rate_kind(getattr(item, "fx_rate_kind", None))
        requested_rate_kind = (
            policy.normalize_rate_kind(updates.get("fx_rate_kind"))
            if "fx_rate_kind" in updates
            else current_rate_kind
        )
        current_payment_mode = policy.normalize_payment_mode(getattr(item, "fx_payment_mode", None))
        requested_payment_mode = (
            policy.normalize_payment_mode(updates.get("fx_payment_mode"))
            if "fx_payment_mode" in updates
            else current_payment_mode
        )
        next_kind = str(updates.get("kind", item.kind))
        policy.validate_payment_mode(
            kind=next_kind,
            currency=normalized_currency,
            base_currency=base_currency,
            payment_mode=requested_payment_mode,
        )
        if (
            "fx_payment_mode" in logged_fields
            and requested_payment_mode != "foreign_balance"
            and fx_settlement_input is not None
        ):
            raise ValueError(f"{requested_payment_mode} must not create a separate currency trade")
        policy_changed = any(
            (
                requested_source != current_source,
                requested_bank_code != current_bank_code,
                requested_bank_channel != current_bank_channel,
                requested_rate_kind != current_rate_kind,
            )
        )
        current_rate = self._rate(getattr(item, "fx_rate", Decimal("1")))
        current_scale = max(1, int(getattr(item, "fx_rate_scale", 1) or 1))
        manual_rate_changed = False
        if fx_manual_rate_present and fx_manual_rate is not None:
            requested_manual_unit = self._rate(Decimal(fx_manual_rate) / Decimal(max(1, display_scale(normalized_currency))))
            manual_rate_changed = requested_manual_unit != current_rate
        explicit_unit_rate = updates.get("fx_rate") if "fx_rate" in updates else None
        explicit_unit_rate_changed = (
            explicit_unit_rate is not None and self._rate(explicit_unit_rate) != current_rate
        )
        should_resolve_rate = (
            normalized_currency != base_currency
            and (currency_changed or policy_changed or manual_rate_changed or explicit_unit_rate_changed or fx_refresh_rate)
        )
        if normalized_currency == base_currency:
            normalized_fx_rate = self._rate(Decimal("1"))
            updates.update(
                {
                    "fx_rate_source": None,
                    "fx_bank_code": None,
                    "fx_bank_name": None,
                    "fx_bank_channel": None,
                    "fx_rate_kind": None,
                    "fx_rate_scale": 1,
                    "fx_rate_date": None,
                    "fx_quoted_at": None,
                    "fx_fetched_at": None,
                    "fx_rate_stale": False,
                    "fx_payment_mode": "valuation",
                }
            )
            requested_payment_mode = "valuation"
        elif should_resolve_rate:
            effective_source = requested_source
            if effective_source is None:
                if explicit_unit_rate is None and fx_manual_rate is None:
                    raise ValueError("fx_rate_source is required when changing operation currency")
                effective_source = "manual"
            if explicit_unit_rate_changed and effective_source != "manual":
                raise ValueError("fx_rate cannot override a bank or NBRB policy; choose manual source")
            resolution = policy.resolve(
                user_id=user_id,
                currency=normalized_currency,
                base_currency=base_currency,
                source=effective_source,
                bank_code=requested_bank_code,
                bank_channel=requested_bank_channel,
                rate_kind=requested_rate_kind,
                manual_rate=fx_manual_rate,
                legacy_unit_rate=(explicit_unit_rate if explicit_unit_rate is not None else current_rate),
                as_of=updates.get("operation_date", item.operation_date),
            )
            normalized_fx_rate = resolution.rate
            updates.update(resolution.operation_snapshot(payment_mode=requested_payment_mode))
        else:
            # Historical operation snapshots are deliberately frozen.  Amount
            # changes and broad unchanged form payloads use the saved rate.
            normalized_fx_rate = current_rate
            updates["fx_rate_source"] = requested_source
            updates["fx_bank_code"] = requested_bank_code
            updates["fx_bank_channel"] = requested_bank_channel
            updates["fx_rate_kind"] = requested_rate_kind
            updates["fx_rate_scale"] = current_scale
            updates["fx_payment_mode"] = requested_payment_mode
            updates["fx_rate"] = current_rate
        needs_currency_recalc = any(
            key in logged_fields
            for key in (
                "amount",
                "currency",
                "fx_rate",
                "fx_rate_source",
                "fx_bank_code",
                "fx_bank_channel",
                "fx_rate_kind",
                "fx_manual_rate",
                "fx_refresh_rate",
            )
        )
        if needs_currency_recalc:
            current_original_amount = updates.get(
                "amount",
                self._money(getattr(item, "original_amount", item.amount)),
            )
            updates["original_amount"] = self._money(current_original_amount)
            updates["currency"] = normalized_currency
            updates["base_currency"] = base_currency
            updates["fx_rate"] = normalized_fx_rate
            updates["amount"] = self._money(Decimal(current_original_amount) * Decimal(normalized_fx_rate))

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
            receipt_changes = ActivityService.summarize_receipt_changes(before_receipt_items, storage_items)
            if receipt_total is not None and "amount" not in updates:
                # Keep operation amount as source of truth; discrepancy is reported in output.
                _ = receipt_total

        linked_trade = self.currency_repo.get_trade_by_linked_operation_id(
            user_id=user_id,
            operation_id=item.id,
        )
        settlement_relevant_change = any(
            key in logged_fields
            for key in (
                "amount",
                "currency",
                "fx_rate",
                "fx_rate_source",
                "fx_bank_code",
                "fx_bank_channel",
                "fx_rate_kind",
                "fx_manual_rate",
                "fx_refresh_rate",
                "operation_date",
                "fx_payment_mode",
            )
        )
        try:
            if requested_payment_mode == "foreign_balance" and (
                linked_trade is None or settlement_relevant_change or "fx_settlement" in logged_fields
            ):
                settlement_payload = {
                    "asset_currency": str(item.currency).upper(),
                    "quantity": self._money(item.original_amount),
                    "quote_total": self._money(item.amount),
                    "unit_price": self._rate(item.fx_rate),
                    "note": (
                        fx_settlement_input.get("note")
                        if isinstance(fx_settlement_input, dict)
                        else (linked_trade.note if linked_trade is not None else None)
                    ),
                }
                normalized_settlement = self._normalize_fx_settlement(
                    user_id=user_id,
                    kind=str(item.kind),
                    operation_amount=self._money(item.amount),
                    operation_date=item.operation_date,
                    base_currency=str(item.base_currency).upper(),
                    payload=settlement_payload,
                )
                CurrencyService(self.db).sync_linked_operation_trade(
                    user_id=user_id,
                    operation_id=item.id,
                    asset_currency=normalized_settlement["asset_currency"],
                    quote_currency=str(item.base_currency).upper(),
                    quantity=normalized_settlement["quantity"],
                    unit_price=normalized_settlement["unit_price"],
                    trade_date=item.operation_date,
                    note=normalized_settlement["note"],
                    commit=False,
                )
            elif "fx_payment_mode" in logged_fields and requested_payment_mode in {
                "valuation",
                "direct_conversion",
            }:
                if linked_trade is not None:
                    self.currency_repo.delete_trade(linked_trade)
            elif "fx_settlement" in logged_fields:
                # Legacy BYN operation + explicit settlement remains supported
                # when no new payment mode was selected.
                if fx_settlement_input is None:
                    if linked_trade is not None:
                        self.currency_repo.delete_trade(linked_trade)
                else:
                    current_base_currency = str(item.base_currency).upper()
                    normalized_settlement = self._normalize_fx_settlement(
                        user_id=user_id,
                        kind=str(item.kind),
                        operation_amount=self._money(item.amount),
                        operation_date=item.operation_date,
                        base_currency=current_base_currency,
                        payload=fx_settlement_input,
                    )
                    CurrencyService(self.db).sync_linked_operation_trade(
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
        except Exception:
            self.db.rollback()
            raise

        if item.kind == "income":
            self.repo.reattach_work_payment_links(user_id=user_id, operation_id=int(item.id))
        self.repo.sync_work_payment_link_snapshots(user_id=user_id, operation=item)

        after_activity = ActivityService.snapshot(item, self.ACTIVITY_FIELDS)
        activity_event = self.activity.record_updated(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="operation",
            entity_id=int(item.id),
            before=before_activity,
            after=after_activity,
            labels=self.ACTIVITY_LABELS,
            title="Операция изменена",
            metadata={
                "receipt_updated": normalized_items is not None,
                "receipt_changes": receipt_changes,
                "fx_settlement_updated": "fx_settlement" in logged_fields,
            },
        )
        if activity_event is None and (normalized_items is not None or "fx_settlement" in logged_fields):
            self.activity.record(
                user_id=user_id,
                actor_user_id=user_id,
                entity_type="operation",
                entity_id=int(item.id),
                event_type="updated",
                title="Операция изменена",
                metadata={
                    "receipt_updated": normalized_items is not None,
                    "receipt_changes": receipt_changes,
                    "fx_settlement_updated": "fx_settlement" in logged_fields,
                },
            )
        self.db.commit()
        self._invalidate_caches(user_id)
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

        self.repo.sync_work_payment_link_snapshots(user_id=user_id, operation=item)

        receipt_items = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[operation_id],
        ).get(operation_id, [])
        linked_trade = self.currency_repo.get_trade_by_linked_operation_id(
            user_id=user_id,
            operation_id=operation_id,
        )
        restore_snapshot = self._build_operation_restore_snapshot(
            item=item,
            receipt_items=receipt_items,
            linked_trade=linked_trade,
            item_price_ids=self.repo.list_item_price_ids_for_operation(operation_id=operation_id),
        )

        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="operation",
            entity_id=int(item.id),
            event_type="deleted",
            title="Операция удалена",
            metadata={
                **ActivityService.snapshot(item, self.ACTIVITY_FIELDS),
                "_restore_snapshot": restore_snapshot,
            },
        )
        if linked_trade is not None:
            self.currency_repo.delete_trade(linked_trade)
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

    @staticmethod
    def _build_operation_restore_snapshot(
        *,
        item,
        receipt_items: list,
        linked_trade,
        item_price_ids: list[int],
    ) -> dict:
        def iso(value):
            return value.isoformat() if value is not None else None

        operation = {
            "id": int(item.id),
            "kind": item.kind,
            "amount": str(item.amount),
            "original_amount": str(item.original_amount),
            "currency": item.currency,
            "base_currency": item.base_currency,
            "fx_rate": str(item.fx_rate),
            "fx_rate_source": getattr(item, "fx_rate_source", None),
            "fx_bank_code": getattr(item, "fx_bank_code", None),
            "fx_bank_name": getattr(item, "fx_bank_name", None),
            "fx_bank_channel": getattr(item, "fx_bank_channel", None),
            "fx_rate_kind": getattr(item, "fx_rate_kind", None),
            "fx_rate_scale": int(getattr(item, "fx_rate_scale", 1) or 1),
            "fx_rate_date": iso(getattr(item, "fx_rate_date", None)),
            "fx_quoted_at": iso(getattr(item, "fx_quoted_at", None)),
            "fx_fetched_at": iso(getattr(item, "fx_fetched_at", None)),
            "fx_rate_stale": bool(getattr(item, "fx_rate_stale", False)),
            "fx_payment_mode": getattr(item, "fx_payment_mode", "valuation") or "valuation",
            "operation_date": iso(item.operation_date),
            "category_id": item.category_id,
            "note": item.note,
            "created_at": iso(item.created_at),
        }
        receipts = [
            {
                "id": int(row.id),
                "template_id": row.template_id,
                "category_id": row.category_id,
                "shop_name": row.shop_name,
                "name": row.name,
                "quantity": str(row.quantity),
                "unit_price": str(row.unit_price),
                "is_discounted": bool(row.is_discounted),
                "regular_unit_price": str(row.regular_unit_price) if row.regular_unit_price is not None else None,
                "discount_type": row.discount_type,
                "line_total": str(row.line_total),
                "note": row.note,
                "created_at": iso(row.created_at),
            }
            for row in receipt_items
        ]
        trade = None
        if linked_trade is not None:
            trade = {
                "id": int(linked_trade.id),
                "side": linked_trade.side,
                "asset_currency": linked_trade.asset_currency,
                "quote_currency": linked_trade.quote_currency,
                "quantity": str(linked_trade.quantity),
                "unit_price": str(linked_trade.unit_price),
                "fee": str(linked_trade.fee),
                "trade_kind": linked_trade.trade_kind,
                "trade_date": iso(linked_trade.trade_date),
                "note": linked_trade.note,
                "created_at": iso(linked_trade.created_at),
            }
        return {
            "version": 2,
            "operation": operation,
            "receipt_items": receipts,
            "fx_settlement": trade,
            "item_price_ids": item_price_ids,
        }

    def restore_deleted_operation(self, *, user_id: int, operation_id: int) -> dict:
        if self.repo.get_by_id(user_id=user_id, operation_id=operation_id) is not None:
            raise ValueError("Operation already exists")
        event = self.activity.get_restore_event(
            user_id=user_id,
            entity_type="operation",
            entity_id=operation_id,
        )
        snapshot = dict((event.metadata_json or {})["_restore_snapshot"])
        snapshot_version = snapshot.get("version")
        if snapshot_version not in {1, 2} or not isinstance(snapshot.get("operation"), dict):
            raise ValueError("Unsupported operation restore snapshot")
        operation_data = dict(snapshot["operation"])
        if int(operation_data.get("id") or 0) != operation_id:
            raise ValueError("Operation restore snapshot does not match the requested operation")
        trade_data = snapshot.get("fx_settlement")
        if snapshot_version == 1:
            restored_currency = str(operation_data.get("currency") or "BYN").upper()
            restored_base_currency = str(operation_data.get("base_currency") or "BYN").upper()
            operation_data["fx_rate_scale"] = display_scale(restored_currency)
            operation_data["fx_payment_mode"] = (
                "foreign_balance"
                if isinstance(trade_data, dict) and restored_currency != restored_base_currency
                else "valuation"
            )

        category_ids = {
            int(category_id)
            for category_id in [operation_data.get("category_id")]
            + [row.get("category_id") for row in snapshot.get("receipt_items") or []]
            if int(category_id or 0) > 0
        }
        if category_ids:
            available_category_ids = set(
                self.db.scalars(
                    select(Category.id).where(
                        Category.id.in_(category_ids),
                        (Category.user_id == user_id) | (Category.is_system.is_(True)),
                    )
                )
            )
            if category_ids != {int(item_id) for item_id in available_category_ids}:
                raise ValueError("A category used by the deleted operation no longer exists")
        template_ids = {
            int(row["template_id"])
            for row in snapshot.get("receipt_items") or []
            if int(row.get("template_id") or 0) > 0
        }
        if template_ids:
            available_template_ids = set(
                self.db.scalars(
                    select(OperationItemTemplate.id).where(
                        OperationItemTemplate.user_id == user_id,
                        OperationItemTemplate.id.in_(template_ids),
                    )
                )
            )
            if template_ids != {int(item_id) for item_id in available_template_ids}:
                raise ValueError("A receipt template used by the deleted operation no longer exists")

        item = self.repo.restore(user_id=user_id, snapshot=operation_data)
        self.repo.reattach_work_payment_links(user_id=user_id, operation_id=operation_id)
        self.repo.sync_work_payment_link_snapshots(user_id=user_id, operation=item)
        restored_receipts = self.repo.restore_receipt_items(
            user_id=user_id,
            operation_id=operation_id,
            items=list(snapshot.get("receipt_items") or []),
        )
        if isinstance(trade_data, dict):
            trade = FxTrade(
                id=int(trade_data["id"]),
                user_id=user_id,
                side=trade_data["side"],
                asset_currency=trade_data["asset_currency"],
                quote_currency=trade_data["quote_currency"],
                quantity=Decimal(trade_data["quantity"]),
                unit_price=Decimal(trade_data["unit_price"]),
                fee=Decimal(trade_data["fee"]),
                trade_kind=trade_data["trade_kind"],
                linked_operation_id=operation_id,
                trade_date=date.fromisoformat(trade_data["trade_date"]),
                note=trade_data.get("note"),
            )
            if trade_data.get("created_at"):
                trade.created_at = datetime.fromisoformat(trade_data["created_at"])
            self.currency_repo.lock_user_currency_ledger(user_id=user_id)
            try:
                CurrencyService(self.db)._validate_trade_sequence(
                    [*self.currency_repo.list_all_trades(user_id=user_id), trade]
                )
            except Exception:
                self.db.rollback()
                raise
            self.db.add(trade)
        self.repo.restore_item_price_links(
            operation_id=operation_id,
            price_ids=[int(item_id) for item_id in snapshot.get("item_price_ids") or []],
        )
        self.activity.mark_restored(event, entity_id=operation_id)
        self.activity.record(
            user_id=user_id,
            actor_user_id=user_id,
            entity_type="operation",
            entity_id=operation_id,
            event_type="restored",
            title="Операция восстановлена",
            metadata={
                "receipt_items": len(restored_receipts),
                "has_fx_settlement": isinstance(trade_data, dict),
            },
        )
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_dashboard_analytics_cache(user_id)
        invalidate_item_templates_cache(user_id)
        invalidate_operations_cache(user_id)
        self.db.refresh(item)
        log_background_job_event(
            "operation_service",
            "operation_restored",
            user_id=user_id,
            operation_id=operation_id,
            receipt_items=len(restored_receipts),
            has_fx_settlement=isinstance(trade_data, dict),
        )
        return self._serialize_operation(user_id=user_id, operation=item, receipt_items=restored_receipts)

    def list_item_templates(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        q: str | None,
        brand_id: int | None = None,
    ) -> tuple[list[dict], int]:
        return self.item_templates.list_item_templates(
            user_id=user_id,
            page=page,
            page_size=page_size,
            q=q,
            brand_id=brand_id,
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

    def delete_item_template_price(
        self,
        *,
        user_id: int,
        template_id: int,
        price_id: int,
    ) -> dict:
        return self.item_templates.delete_item_template_price(
            user_id=user_id,
            template_id=template_id,
            price_id=price_id,
        )

    def create_item_template(
        self,
        *,
        user_id: int,
        shop_name: str | None,
        source_id: int | None,
        name: str,
        last_category_id: int | None,
        brand_id: int | None,
        latest_unit_price: Decimal | None,
        latest_price_date: date | None = None,
        product_id: int | None = None,
    ) -> dict:
        return self.item_templates.create_item_template(
            user_id=user_id,
            shop_name=shop_name,
            source_id=source_id,
            name=name,
            last_category_id=last_category_id,
            brand_id=brand_id,
            latest_unit_price=latest_unit_price,
            latest_price_date=latest_price_date,
            product_id=product_id,
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

    def bulk_update_item_template_brand(
        self,
        *,
        user_id: int,
        template_ids: list[int],
        brand_id: int | None,
    ) -> int:
        return self.item_templates.bulk_update_item_template_brand(
            user_id=user_id,
            template_ids=template_ids,
            brand_id=brand_id,
        )

    def delete_item_template(self, *, user_id: int, template_id: int) -> None:
        self.item_templates.delete_item_template(user_id=user_id, template_id=template_id)

    def delete_all_item_templates(self, *, user_id: int) -> int:
        return self.item_templates.delete_all_item_templates(user_id=user_id)

    def _serialize_operation(
        self,
        *,
        user_id: int,
        operation,
        receipt_items: list | None = None,
        brand_meta_map: dict[int, dict] | None = None,
    ) -> dict:
        loaded_items = receipt_items
        if loaded_items is None:
            loaded = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(operation.id)],
            )
            loaded_items = loaded.get(int(operation.id), [])
        category_meta_map = self._get_category_meta_map([row.category_id for row in loaded_items or []] + [operation.category_id])
        if brand_meta_map is None:
            brand_meta_map = self._get_brand_meta_map(
                user_id=user_id,
                template_ids=[row.template_id for row in loaded_items or []],
            )
        receipt_payload = []
        receipt_total = Decimal("0")
        for row in loaded_items or []:
            line_total = self._money(row.line_total)
            receipt_total += line_total
            category_meta = category_meta_map.get(int(row.category_id or 0), {})
            brand_meta = brand_meta_map.get(int(row.template_id or 0), {})
            receipt_payload.append(
                {
                    "id": int(row.id),
                    "template_id": row.template_id,
                    "product_id": brand_meta.get("product_id"),
                    "product_name": brand_meta.get("product_name"),
                    "product_image_id": brand_meta.get("product_image_id"),
                    "brand_id": brand_meta.get("brand_id"),
                    "brand_name": brand_meta.get("brand_name"),
                    "brand_accent_color": brand_meta.get("brand_accent_color"),
                    "brand_is_archived": bool(brand_meta.get("brand_is_archived", False)),
                    "item_image_id": brand_meta.get("item_image_id"),
                    "brand_image_id": brand_meta.get("brand_image_id"),
                    "source_id": brand_meta.get("source_id"),
                    "source_name": brand_meta.get("source_name") or row.shop_name,
                    "source_image_id": brand_meta.get("source_image_id"),
                    "category_id": row.category_id,
                    "category_name": category_meta.get("name"),
                    "category_icon": category_meta.get("icon"),
                    "category_accent_color": category_meta.get("accent_color"),
                    "shop_name": row.shop_name,
                    "name": row.name,
                    "quantity": self._qty(row.quantity),
                    "unit_price": self._money(row.unit_price),
                    "is_discounted": bool(getattr(row, "is_discounted", False)),
                    "regular_unit_price": (
                        self._money(row.regular_unit_price)
                        if getattr(row, "regular_unit_price", None) is not None
                        else None
                    ),
                    "discount_type": getattr(row, "discount_type", None),
                    "line_total": line_total,
                    "note": row.note,
                }
            )
        amount = self._money(operation.amount)
        original_amount = self._money(getattr(operation, "original_amount", operation.amount))
        currency = str(getattr(operation, "currency", "BYN") or "BYN").upper()
        base_currency = str(getattr(operation, "base_currency", "BYN") or "BYN").upper()
        fx_rate = self._rate(getattr(operation, "fx_rate", Decimal("1.000000")))
        fx_rate_scale = max(1, int(getattr(operation, "fx_rate_scale", 1) or 1))
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
            "fx_rate_source": getattr(operation, "fx_rate_source", None),
            "fx_bank_code": getattr(operation, "fx_bank_code", None),
            "fx_bank_name": getattr(operation, "fx_bank_name", None),
            "fx_bank_channel": getattr(operation, "fx_bank_channel", None),
            "fx_rate_kind": getattr(operation, "fx_rate_kind", None),
            "fx_rate_scale": fx_rate_scale,
            "fx_rate_display": self._rate(fx_rate * Decimal(fx_rate_scale)),
            "fx_rate_date": getattr(operation, "fx_rate_date", None),
            "fx_quoted_at": getattr(operation, "fx_quoted_at", None),
            "fx_fetched_at": getattr(operation, "fx_fetched_at", None),
            "fx_rate_stale": bool(getattr(operation, "fx_rate_stale", False)),
            "fx_payment_mode": getattr(operation, "fx_payment_mode", "valuation") or "valuation",
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

    def _get_brand_meta_map(
        self,
        *,
        user_id: int,
        template_ids: list[int | None],
    ) -> dict[int, dict]:
        return self.item_templates.brand_repo.brand_meta_for_templates(
            user_id=user_id,
            template_ids=[int(template_id) for template_id in template_ids if template_id is not None],
        )

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
            is_discounted = bool(item.get("is_discounted"))
            regular_unit_price = None
            if item.get("regular_unit_price") not in (None, ""):
                regular_unit_price = self._money(item.get("regular_unit_price") or Decimal("0"))
                if regular_unit_price <= 0:
                    raise ValueError("receipt item regular_unit_price must be greater than 0")
            discount_type = str(item.get("discount_type") or "").strip() or None
            if discount_type not in (None, "promo", "coupon", "loyalty_points"):
                raise ValueError("receipt item discount_type is invalid")
            line_total = self._money(quantity * unit_price)
            note = item.get("note")
            normalized.append(
                {
                    "category_id": item.get("category_id"),
                    "category_touched": bool(item.get("category_touched")),
                    "shop_name": shop_name,
                    "name": name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "is_discounted": is_discounted,
                    "regular_unit_price": regular_unit_price if is_discounted else None,
                    "discount_type": discount_type if is_discounted else None,
                    "line_total": line_total,
                    "note": note,
                    **(
                        {"template_id": int(item["template_id"])}
                        if item.get("template_id") is not None
                        else {}
                    ),
                    **({"product_id": int(item["product_id"])} if item.get("product_id") is not None else {}),
                    **({"source_id": int(item["source_id"])} if item.get("source_id") is not None else {}),
                    **({"brand_id": item.get("brand_id")} if "brand_id" in item else {}),
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
            resolved_amount = self._money(receipt_total)
            if resolved_amount <= 0:
                raise ValueError("amount must be greater than 0")
            return resolved_amount
        if amount is None:
            raise ValueError("amount is required")
        resolved_amount = self._money(amount)
        if resolved_amount <= 0:
            raise ValueError("amount must be greater than 0")
        return resolved_amount

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
