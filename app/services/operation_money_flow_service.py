from datetime import date, datetime
from decimal import Decimal

from app.repositories.currency_repo import CurrencyRepository
from app.services.currency_service import CurrencyService


class OperationMoneyFlowService:
    """Builds the unified read-only cashflow timeline exposed by OperationService."""

    MAX_IN_MEMORY_FLOW_ITEMS = 5000

    def __init__(self, operation_service):
        self.operations = operation_service
        self.db = operation_service.db
        self.repo = operation_service.repo

    @staticmethod
    def _normalize_direction(direction: str | None) -> str:
        value = str(direction or "all").strip().lower()
        if value not in {"all", "inflow", "outflow"}:
            raise ValueError("direction must be one of: all, inflow, outflow")
        return value

    @staticmethod
    def _normalize_source(source: str | None) -> str:
        value = str(source or "all").strip().lower()
        if value not in {"all", "operation", "debt", "fx"}:
            raise ValueError("source must be one of: all, operation, debt, fx")
        return value

    @staticmethod
    def _matches_query(item: dict, q: str | None) -> bool:
        query = " ".join((q or "").strip().split()).casefold()
        if not query:
            return True
        haystack = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("subtitle") or ""),
                str(item.get("note") or ""),
                str(item.get("category_name") or ""),
                str(item.get("counterparty_name") or ""),
                str(item.get("asset_currency") or ""),
                str(item.get("quote_currency") or ""),
                str(item.get("trade_side") or ""),
                str(item.get("source_kind") or ""),
            ]
        ).casefold()
        return query in haystack

    @staticmethod
    def _sort_items(items: list[dict], *, sort_by: str, sort_dir: str) -> None:
        def sort_key(item: dict):
            if sort_by == "amount":
                return Decimal(item.get("amount") or 0)
            if sort_by == "created_at":
                return item.get("source_id") or 0
            return str(item.get("event_date") or "")

        items.sort(
            key=lambda item: (
                sort_key(item),
                str(item.get("event_date") or ""),
                str(item.get("id") or ""),
            ),
            reverse=sort_dir != "asc",
        )

    @classmethod
    def _ensure_dataset_size(cls, items: list[dict]) -> None:
        if len(items) > cls.MAX_IN_MEMORY_FLOW_ITEMS:
            raise ValueError(
                "Слишком много событий для общего поиска. Уточните период, источник или поисковый запрос."
            )

    @classmethod
    def _append_bounded(cls, items: list[dict], item: dict) -> None:
        items.append(item)
        cls._ensure_dataset_size(items)

    def _build_dataset(
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
        category_id: int | None = None,
        item_template_id: int | None = None,
    ) -> list[dict]:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        normalized_direction = self._normalize_direction(direction)
        normalized_source = self._normalize_source(source)
        normalized_currency_scope = self.operations._normalize_currency_scope(currency_scope)
        operations_only_filter = category_id is not None or item_template_id is not None
        base_currency = self.operations._get_user_base_currency(user_id)
        items: list[dict] = []

        def include_direction(flow_direction: str) -> bool:
            return normalized_direction == "all" or flow_direction == normalized_direction

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
                category_id=category_id,
                q=q,
                item_template_id=item_template_id,
                receipt_only=False,
                uncategorized_only=False,
                min_amount=None,
                currency_scope=normalized_currency_scope,
                base_currency=base_currency,
                limit=self.MAX_IN_MEMORY_FLOW_ITEMS + 1,
            )
            self._ensure_dataset_size(operations)
            receipt_by_operation = self.repo.list_receipt_items_for_operations(
                user_id=user_id,
                operation_ids=[int(item.id) for item in operations],
            )
            for operation in operations:
                item = self._operation_to_money_flow_item(
                    user_id=user_id,
                    operation=operation,
                    receipt_items=receipt_by_operation.get(int(operation.id), []),
                )
                if self._matches_query(item, q):
                    self._append_bounded(items, item)

        if not operations_only_filter and normalized_source in {"all", "debt"}:
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
                            "amount": self.operations._money(
                                issuance.get("current_base_amount") or issuance.get("amount") or 0
                            ),
                            "original_amount": self.operations._money(issuance.get("amount") or 0),
                            "currency": debt_currency,
                            "base_currency": debt_base_currency,
                            "fx_rate": self.operations._rate(Decimal("1")),
                            "title": "Я дал в долг" if is_lend else "Я взял в долг",
                            "subtitle": str(card.get("counterparty") or "Контрагент"),
                            "note": issuance.get("note") or debt.get("note"),
                            "counterparty_id": int(card["counterparty_id"]),
                            "counterparty_name": str(card.get("counterparty") or ""),
                            "can_open_source": True,
                            "open_section": "debts",
                            "open_label": "Движения долга",
                        }
                        if self._matches_query(item, q):
                            self._append_bounded(items, item)
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
                            "amount": self.operations._money(
                                repayment.get("current_base_amount") or repayment.get("amount") or 0
                            ),
                            "original_amount": self.operations._money(repayment.get("amount") or 0),
                            "currency": debt_currency,
                            "base_currency": debt_base_currency,
                            "fx_rate": self.operations._rate(Decimal("1")),
                            "title": "Мне вернули долг" if is_lend else "Я вернул долг",
                            "subtitle": str(card.get("counterparty") or "Контрагент"),
                            "note": repayment.get("note") or debt.get("note"),
                            "counterparty_id": int(card["counterparty_id"]),
                            "counterparty_name": str(card.get("counterparty") or ""),
                            "can_open_source": True,
                            "open_section": "debts",
                            "open_label": "Движения долга",
                        }
                        if self._matches_query(item, q):
                            self._append_bounded(items, item)

        if not operations_only_filter and normalized_source in {"all", "fx"}:
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
                gross = Decimal(getattr(trade, "quantity", 0) or 0) * Decimal(
                    getattr(trade, "unit_price", 0) or 0
                )
                fee = Decimal(getattr(trade, "fee", 0) or 0)
                amount = self.operations._money(gross + fee if trade.side == "buy" else gross - fee)
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
                    "fx_rate": self.operations._rate(Decimal("1")),
                    "title": (
                        f"{'Покупка' if trade.side == 'buy' else 'Продажа'} "
                        f"{str(trade.asset_currency).upper()}"
                    ),
                    "subtitle": (
                        f"{'За' if trade.side == 'buy' else 'В'} {quote_currency} · "
                        f"курс {self.operations._rate(Decimal(trade.unit_price))}"
                    ),
                    "note": trade.note,
                    "asset_currency": str(trade.asset_currency).upper(),
                    "asset_quantity": self.operations._qty(Decimal(getattr(trade, "quantity", 0) or 0)),
                    "quote_currency": quote_currency,
                    "trade_side": str(trade.side),
                    "can_open_source": True,
                    "open_section": "currency",
                    "open_label": "Редактировать",
                }
                if self._matches_query(item, q):
                    self._append_bounded(items, item)

        self._sort_items(items, sort_by=sort_by, sort_dir=sort_dir)
        return items

    def _operation_to_money_flow_item(self, *, user_id: int, operation, receipt_items: list) -> dict:
        payload = self.operations._serialize_operation(
            user_id=user_id,
            operation=operation,
            receipt_items=receipt_items,
        )
        flow_direction = "inflow" if payload["kind"] == "income" else "outflow"
        return {
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

    def _list_operation_flow_page(
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
        direction: str | None,
        currency_scope: str | None,
        category_id: int | None,
        item_template_id: int | None,
    ) -> tuple[list[dict], int]:
        normalized_direction = self._normalize_direction(direction)
        operation_kind = None
        if normalized_direction == "inflow":
            operation_kind = "income"
        elif normalized_direction == "outflow":
            operation_kind = "expense"
        base_currency = self.operations._get_user_base_currency(user_id)
        rows, total = self.repo.list_filtered(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=operation_kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            item_template_id=item_template_id,
            receipt_only=False,
            uncategorized_only=False,
            min_amount=None,
            currency_scope=self.operations._normalize_currency_scope(currency_scope),
            base_currency=base_currency,
        )
        receipt_by_operation = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[int(item.id) for item in rows],
        )
        return [
            self._operation_to_money_flow_item(
                user_id=user_id,
                operation=operation,
                receipt_items=receipt_by_operation.get(int(operation.id), []),
            )
            for operation in rows
        ], total

    def _list_mixed_flow_page(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        sort_by: str,
        sort_dir: str,
        date_from: date | None,
        date_to: date | None,
        direction: str | None,
        currency_scope: str | None,
    ) -> tuple[list[dict], int]:
        normalized_direction = self._normalize_direction(direction)
        operation_kind = None
        if normalized_direction == "inflow":
            operation_kind = "income"
        elif normalized_direction == "outflow":
            operation_kind = "expense"
        normalized_currency_scope = self.operations._normalize_currency_scope(currency_scope)
        base_currency = self.operations._get_user_base_currency(user_id)
        operation_scan_size = max(page, 1) * page_size
        operation_rows, operation_total = self.repo.list_filtered(
            user_id=user_id,
            page=1,
            page_size=operation_scan_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            kind=operation_kind,
            date_from=date_from,
            date_to=date_to,
            category_id=None,
            q=None,
            item_template_id=None,
            receipt_only=False,
            uncategorized_only=False,
            min_amount=None,
            currency_scope=normalized_currency_scope,
            base_currency=base_currency,
        )
        receipt_by_operation = self.repo.list_receipt_items_for_operations(
            user_id=user_id,
            operation_ids=[int(item.id) for item in operation_rows],
        )
        items = [
            self._operation_to_money_flow_item(
                user_id=user_id,
                operation=operation,
                receipt_items=receipt_by_operation.get(int(operation.id), []),
            )
            for operation in operation_rows
        ]
        non_operation_items = self._build_dataset(
            user_id=user_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            q=None,
            direction=direction,
            source="debt",
            currency_scope=currency_scope,
        )
        non_operation_items.extend(
            self._build_dataset(
                user_id=user_id,
                sort_by=sort_by,
                sort_dir=sort_dir,
                date_from=date_from,
                date_to=date_to,
                q=None,
                direction=direction,
                source="fx",
                currency_scope=currency_scope,
            )
        )
        self._ensure_dataset_size(non_operation_items)
        items.extend(non_operation_items)
        self._sort_items(items, sort_by=sort_by, sort_dir=sort_dir)
        total = operation_total + len(non_operation_items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def _summarize_items(self, items: list[dict]) -> tuple[Decimal, Decimal, int]:
        income_total = sum(
            (Decimal(item["amount"]) for item in items if item.get("flow_direction") == "inflow"),
            start=Decimal("0"),
        )
        expense_total = sum(
            (Decimal(item["amount"]) for item in items if item.get("flow_direction") == "outflow"),
            start=Decimal("0"),
        )
        return income_total, expense_total, len(items)

    def _summarize_operations(
        self,
        *,
        user_id: int,
        date_from: date | None,
        date_to: date | None,
        q: str | None,
        direction: str | None,
        currency_scope: str | None,
        category_id: int | None,
        item_template_id: int | None,
    ) -> tuple[Decimal, Decimal, int]:
        normalized_direction = self._normalize_direction(direction)
        operation_kind = None
        if normalized_direction == "inflow":
            operation_kind = "income"
        elif normalized_direction == "outflow":
            operation_kind = "expense"
        return self.repo.summary_filtered(
            user_id=user_id,
            kind=operation_kind,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            q=q,
            item_template_id=item_template_id,
            currency_scope=self.operations._normalize_currency_scope(currency_scope),
            base_currency=self.operations._get_user_base_currency(user_id),
        )

    def list(
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
    ) -> tuple[list[dict], int]:
        normalized_source = self._normalize_source(source)
        operations_only_filter = category_id is not None or item_template_id is not None
        if normalized_source == "operation" or operations_only_filter:
            return self._list_operation_flow_page(
                user_id=user_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_dir=sort_dir,
                date_from=date_from,
                date_to=date_to,
                q=q,
                direction=direction,
                currency_scope=currency_scope,
                category_id=category_id,
                item_template_id=item_template_id,
            )
        if normalized_source == "all" and not q:
            return self._list_mixed_flow_page(
                user_id=user_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_dir=sort_dir,
                date_from=date_from,
                date_to=date_to,
                direction=direction,
                currency_scope=currency_scope,
            )
        items = self._build_dataset(
            user_id=user_id,
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
        )
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def summarize(
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
    ) -> dict:
        normalized_source = self._normalize_source(source)
        operations_only_filter = category_id is not None or item_template_id is not None
        if normalized_source == "operation" or operations_only_filter:
            income_total, expense_total, total = self._summarize_operations(
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                q=q,
                direction=direction,
                currency_scope=currency_scope,
                category_id=category_id,
                item_template_id=item_template_id,
            )
            return {
                "income_total": self.operations._money(income_total),
                "expense_total": self.operations._money(expense_total),
                "balance": self.operations._money(income_total - expense_total),
                "total": total,
            }
        if normalized_source == "all" and not q:
            operation_income, operation_expense, operation_total = self._summarize_operations(
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                q=None,
                direction=direction,
                currency_scope=currency_scope,
                category_id=None,
                item_template_id=None,
            )
            non_operation_items = self._build_dataset(
                user_id=user_id,
                sort_by="operation_date",
                sort_dir="desc",
                date_from=date_from,
                date_to=date_to,
                q=None,
                direction=direction,
                source="debt",
                currency_scope=currency_scope,
            )
            non_operation_items.extend(
                self._build_dataset(
                    user_id=user_id,
                    sort_by="operation_date",
                    sort_dir="desc",
                    date_from=date_from,
                    date_to=date_to,
                    q=None,
                    direction=direction,
                    source="fx",
                    currency_scope=currency_scope,
                )
            )
            debt_fx_income, debt_fx_expense, debt_fx_total = self._summarize_items(non_operation_items)
            income_total = operation_income + debt_fx_income
            expense_total = operation_expense + debt_fx_expense
            total = operation_total + debt_fx_total
            return {
                "income_total": self.operations._money(income_total),
                "expense_total": self.operations._money(expense_total),
                "balance": self.operations._money(income_total - expense_total),
                "total": total,
            }
        items = self._build_dataset(
            user_id=user_id,
            sort_by="operation_date",
            sort_dir="desc",
            date_from=date_from,
            date_to=date_to,
            q=q,
            direction=direction,
            source=source,
            currency_scope=currency_scope,
            category_id=category_id,
            item_template_id=item_template_id,
        )
        income_total, expense_total, total = self._summarize_items(items)
        return {
            "income_total": self.operations._money(income_total),
            "expense_total": self.operations._money(expense_total),
            "balance": self.operations._money(income_total - expense_total),
            "total": total,
        }
