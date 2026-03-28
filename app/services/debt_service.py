from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.cache import (
    build_debts_cache_key,
    get_json,
    get_namespace_ttl_seconds,
    invalidate_dashboard_summary_cache,
    invalidate_debts_cache,
    set_json,
)
from app.repositories.debt_repo import DebtRepository
from app.repositories.user_repo import UserRepository
from app.repositories.currency_repo import CurrencyRepository
from app.services.debt_reminder_service import DebtReminderService
from app.services.operation_service import OperationService
from app.services.telegram_debt_notifier import notify_debt_repaid_owner


class DebtService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DebtRepository(db)
        self.user_repo = UserRepository(db)
        self.currency_repo = CurrencyRepository(db)
        self.operation_service = OperationService(db)
        self.debt_reminder_service = DebtReminderService(db)

    @staticmethod
    def _normalize_counterparty_name(value: str) -> tuple[str, str]:
        raw = " ".join((value or "").strip().split())
        if not raw:
            raise ValueError("counterparty must not be empty")
        return raw, raw.casefold()

    @staticmethod
    def _validate_direction(direction: str) -> None:
        if direction not in {"lend", "borrow"}:
            raise ValueError("direction must be either 'lend' or 'borrow'")

    @staticmethod
    def _validate_positive_amount(value: Decimal, field_name: str) -> None:
        if value is None or value <= 0:
            raise ValueError(f"{field_name} must be greater than 0")

    @staticmethod
    def _matches_search_token(text: str, token: str) -> bool:
        return token in text.casefold()

    def _debt_matches_query(self, debt: dict, query_token: str) -> bool:
        direction = str(debt.get("direction") or "")
        note = str(debt.get("note") or "")
        terms = [
            direction,
            note,
            "долг" if direction else "",
            "lend" if direction == "lend" else "",
            "borrow" if direction == "borrow" else "",
            "дал" if direction == "lend" else "",
            "взял" if direction == "borrow" else "",
        ]
        for term in terms:
            if term and self._matches_search_token(term, query_token):
                return True
        return False

    @staticmethod
    def _serialize_repayment(repayment) -> dict:
        return {
            "id": int(repayment.id),
            "debt_id": int(repayment.debt_id),
            "amount": Decimal(repayment.amount),
            "repayment_date": repayment.repayment_date,
            "note": repayment.note,
            "created_at": repayment.created_at,
        }

    @staticmethod
    def _serialize_forgiveness(forgiveness) -> dict:
        return {
            "id": int(forgiveness.id),
            "debt_id": int(forgiveness.debt_id),
            "amount": Decimal(forgiveness.amount),
            "forgiven_date": forgiveness.forgiven_date,
            "note": forgiveness.note,
            "created_at": forgiveness.created_at,
        }

    @staticmethod
    def _serialize_issuance(issuance) -> dict:
        return {
            "id": int(issuance.id),
            "debt_id": int(issuance.debt_id),
            "amount": Decimal(issuance.amount),
            "issuance_date": issuance.issuance_date,
            "note": issuance.note,
            "created_at": issuance.created_at,
        }

    def create_debt(
        self,
        user_id: int,
        counterparty: str,
        direction: str,
        principal: Decimal,
        start_date: date,
        currency: str = "BYN",
        due_date: date | None = None,
        note: str | None = None,
    ):
        self._validate_direction(direction)
        self._validate_positive_amount(principal, "principal")
        if due_date and due_date < start_date:
            raise ValueError("due_date must be greater than or equal to start_date")
        base_currency = self.operation_service._get_user_base_currency(user_id)
        normalized_currency = self.operation_service._normalize_currency(currency or base_currency, default=base_currency)

        normalized_name, name_ci = self._normalize_counterparty_name(counterparty)
        cp = self.repo.get_counterparty_by_name_ci(user_id=user_id, name_ci=name_ci)
        if not cp:
            cp = self.repo.create_counterparty(user_id=user_id, name=normalized_name, name_ci=name_ci)
        merge_target = self.repo.find_active_merge_candidate(
            user_id=user_id,
            counterparty_id=cp.id,
            direction=direction,
            currency=normalized_currency,
            base_currency=base_currency,
        )
        if merge_target:
            updates = {
                "principal": Decimal(merge_target.principal) + Decimal(principal),
                "original_principal": Decimal(getattr(merge_target, "original_principal", merge_target.principal)) + Decimal(principal),
            }
            if start_date and start_date < merge_target.start_date:
                updates["start_date"] = start_date
            # Keep existing due date by default; if it is empty, use new one.
            if not merge_target.due_date and due_date:
                updates["due_date"] = due_date
            if note and not merge_target.note:
                updates["note"] = note
            debt = self.repo.update_debt(merge_target, updates)
        else:
            debt = self.repo.create_debt(
                user_id=user_id,
                counterparty_id=cp.id,
                direction=direction,
                principal=principal,
                original_principal=principal,
                currency=normalized_currency,
                base_currency=base_currency,
                start_date=start_date,
                due_date=due_date,
                note=note,
            )
        self.repo.create_issuance(
            debt_id=debt.id,
            amount=principal,
            issuance_date=start_date,
            note=note,
        )
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_debts_cache(user_id)
        self.db.refresh(debt)
        self.debt_reminder_service.sync_debt_job(user_id=user_id, debt_id=int(debt.id))
        return debt, cp

    def _current_totals(self, *, debt_id: int) -> tuple[Decimal, Decimal, Decimal]:
        repaid = self.repo.repayment_total_for_debt(debt_id=debt_id)
        forgiven = self.repo.forgiveness_total_for_debt(debt_id=debt_id)
        return repaid, forgiven, repaid + forgiven

    def add_repayment(
        self,
        user_id: int,
        debt_id: int,
        amount: Decimal,
        repayment_date: date,
        note: str | None = None,
    ):
        self._validate_positive_amount(amount, "amount")
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")
        owner_telegram_id = self.user_repo.get_telegram_id_for_user(user_id)
        counterparty = self.repo.get_counterparty_by_id(user_id=user_id, counterparty_id=debt.counterparty_id)

        repaid, forgiven, settled_total = self._current_totals(debt_id=debt_id)
        principal = Decimal(debt.principal)
        outstanding = principal - settled_total
        if outstanding <= 0:
            raise ValueError("Debt is already closed")

        applied_amount = amount if amount <= outstanding else outstanding
        repayment = self.repo.create_repayment(
            debt_id=debt_id,
            amount=applied_amount,
            repayment_date=repayment_date,
            note=note,
        )

        overpay = amount - applied_amount
        if overpay > 0:
            reverse_direction = "borrow" if debt.direction == "lend" else "lend"
            merge_target = self.repo.find_active_merge_candidate(
                user_id=user_id,
                counterparty_id=debt.counterparty_id,
                direction=reverse_direction,
                currency=str(getattr(debt, "currency", "BYN") or "BYN").upper(),
                base_currency=str(getattr(debt, "base_currency", "BYN") or "BYN").upper(),
            )
            carry_note = note or f"Переплата по долгу #{debt.id}"
            if merge_target:
                updates = {
                    "principal": Decimal(merge_target.principal) + overpay,
                    "original_principal": Decimal(getattr(merge_target, "original_principal", merge_target.principal)) + overpay,
                }
                if repayment_date and repayment_date < merge_target.start_date:
                    updates["start_date"] = repayment_date
                if carry_note and not merge_target.note:
                    updates["note"] = carry_note
                counter_debt = self.repo.update_debt(merge_target, updates)
            else:
                counter_debt = self.repo.create_debt(
                    user_id=user_id,
                    counterparty_id=debt.counterparty_id,
                    direction=reverse_direction,
                    principal=overpay,
                    original_principal=overpay,
                    currency=str(getattr(debt, "currency", "BYN") or "BYN").upper(),
                    base_currency=str(getattr(debt, "base_currency", "BYN") or "BYN").upper(),
                    start_date=repayment_date,
                    due_date=None,
                    note=carry_note,
                )
            self.repo.create_issuance(
                debt_id=counter_debt.id,
                amount=overpay,
                issuance_date=repayment_date,
                note=carry_note,
            )

        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_debts_cache(user_id)
        self.db.refresh(repayment)
        if Decimal(debt.principal) - (repaid + forgiven + applied_amount) <= 0:
            debt.closure_reason = None
            self.db.commit()
        self.debt_reminder_service.sync_debt_job(user_id=user_id, debt_id=int(debt.id))
        if owner_telegram_id and applied_amount == outstanding:
            notify_debt_repaid_owner(
                owner_telegram_id=owner_telegram_id,
                debt_id=debt.id,
                counterparty=(counterparty.name if counterparty else str(debt.counterparty_id)),
                direction=debt.direction,
                amount=applied_amount,
                currency=str(getattr(debt, "currency", "BYN") or "BYN").upper(),
                repayment_date=repayment_date,
                note=note,
            )
        return repayment

    def add_forgiveness(
        self,
        user_id: int,
        debt_id: int,
        amount: Decimal,
        forgiven_date: date,
        note: str | None = None,
    ):
        self._validate_positive_amount(amount, "amount")
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")
        repaid, forgiven, settled_total = self._current_totals(debt_id=debt_id)
        principal = Decimal(debt.principal)
        outstanding = principal - settled_total
        if outstanding <= 0:
            raise ValueError("Debt is already closed")
        applied_amount = amount if amount <= outstanding else outstanding
        forgiveness = self.repo.create_forgiveness(
            debt_id=debt_id,
            amount=applied_amount,
            forgiven_date=forgiven_date,
            note=note,
        )
        remaining_after = principal - (repaid + forgiven + applied_amount)
        debt.closure_reason = "forgiven" if remaining_after <= 0 else None
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_debts_cache(user_id)
        self.db.refresh(forgiveness)
        self.debt_reminder_service.sync_debt_job(user_id=user_id, debt_id=int(debt.id))
        return forgiveness

    def get_debt_with_repayments(self, user_id: int, debt_id: int) -> dict:
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")
        repayments = self.repo.list_repayments_for_debts([debt.id])
        forgivenesses = self.repo.list_forgivenesses_for_debts([debt.id])
        issuances = self.repo.list_issuances_for_debts([debt.id])
        latest_rate_map = self.currency_repo.get_latest_rate_map(user_id=user_id)
        return self._serialize_debt_item(
            debt=debt,
            repayments=repayments,
            forgivenesses=forgivenesses,
            issuances=issuances,
            latest_rate_map=latest_rate_map,
        )

    def update_debt(self, user_id: int, debt_id: int, updates: dict):
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")

        if "counterparty" in updates:
            normalized_name, name_ci = self._normalize_counterparty_name(updates["counterparty"] or "")
            cp = self.repo.get_counterparty_by_name_ci(user_id=user_id, name_ci=name_ci)
            if not cp:
                cp = self.repo.create_counterparty(user_id=user_id, name=normalized_name, name_ci=name_ci)
            updates["counterparty_id"] = cp.id
            updates.pop("counterparty", None)

        direction = updates.get("direction", debt.direction)
        self._validate_direction(direction)

        principal = updates.get("principal", debt.principal)
        self._validate_positive_amount(Decimal(principal), "principal")
        base_currency = self.operation_service._get_user_base_currency(user_id)
        if "currency" in updates and updates["currency"] is not None:
            updates["currency"] = self.operation_service._normalize_currency(updates["currency"], default=base_currency)
        updates["base_currency"] = base_currency
        repaid = self.repo.repayment_total_for_debt(debt_id=debt_id)
        forgiven = self.repo.forgiveness_total_for_debt(debt_id=debt_id)
        if Decimal(principal) < repaid:
            raise ValueError("principal must be greater than or equal to repaid total")
        if Decimal(principal) < (repaid + forgiven):
            raise ValueError("principal must be greater than or equal to settled total")
        if "currency" in updates and updates["currency"] != str(getattr(debt, "currency", "BYN") or "BYN").upper() and repaid > 0:
            raise ValueError("Нельзя менять валюту долга после погашений")
        if "currency" in updates and updates["currency"] != str(getattr(debt, "currency", "BYN") or "BYN").upper() and forgiven > 0:
            raise ValueError("Нельзя менять валюту долга после прощения")
        if "principal" in updates:
            updates["original_principal"] = updates["principal"]
            updates["closure_reason"] = None if Decimal(principal) > (repaid + forgiven) else getattr(debt, "closure_reason", None)

        start_date = updates.get("start_date", debt.start_date)
        due_date = updates.get("due_date", debt.due_date)
        if due_date and start_date and due_date < start_date:
            raise ValueError("due_date must be greater than or equal to start_date")

        allowed = {"counterparty_id", "direction", "principal", "original_principal", "currency", "base_currency", "closure_reason", "start_date", "due_date", "note"}
        payload = {key: value for key, value in updates.items() if key in allowed}
        if payload:
            debt = self.repo.update_debt(debt, payload)
            self.db.commit()
            invalidate_dashboard_summary_cache(user_id)
            invalidate_debts_cache(user_id)
            self.db.refresh(debt)
            self.debt_reminder_service.sync_debt_job(user_id=user_id, debt_id=int(debt.id))
        return debt

    def delete_debt(self, user_id: int, debt_id: int) -> None:
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")
        self.repo.delete_debt(debt)
        self.db.commit()
        invalidate_dashboard_summary_cache(user_id)
        invalidate_debts_cache(user_id)
        self.debt_reminder_service.sync_debt_job(user_id=user_id, debt_id=debt_id)

    def list_cards(self, user_id: int, include_closed: bool = False, q: str | None = None) -> list[dict]:
        query_token = " ".join((q or "").strip().split()).casefold()
        cache_key = build_debts_cache_key(
            user_id=user_id,
            view="cards",
            include_closed=include_closed,
            q=query_token or None,
        )
        cached = get_json(cache_key)
        if cached is not None:
            return cached["items"]
        counterparties = self.repo.list_counterparties(user_id=user_id)
        if not counterparties:
            return []

        counterparty_ids = [item.id for item in counterparties]
        debts = self.repo.list_debts_for_counterparties(user_id=user_id, counterparty_ids=counterparty_ids)
        debt_ids = [item.id for item in debts]
        repayments = self.repo.list_repayments_for_debts(debt_ids=debt_ids)
        forgivenesses = self.repo.list_forgivenesses_for_debts(debt_ids=debt_ids)
        issuances = self.repo.list_issuances_for_debts(debt_ids=debt_ids)

        repayments_by_debt: dict[int, list] = defaultdict(list)
        for rep in repayments:
            repayments_by_debt[rep.debt_id].append(rep)
        issuances_by_debt: dict[int, list] = defaultdict(list)
        for issuance in issuances:
            issuances_by_debt[issuance.debt_id].append(issuance)
        forgivenesses_by_debt: dict[int, list] = defaultdict(list)
        for forgiveness in forgivenesses:
            forgivenesses_by_debt[forgiveness.debt_id].append(forgiveness)

        debts_by_counterparty: dict[int, list] = defaultdict(list)
        for debt in debts:
            debts_by_counterparty[debt.counterparty_id].append(debt)

        cards: list[dict] = []
        latest_rate_map = self.currency_repo.get_latest_rate_map(user_id=user_id)
        base_currency = self.operation_service._get_user_base_currency(user_id)
        for cp in counterparties:
            card_debts = debts_by_counterparty.get(cp.id, [])
            debt_items: list[dict] = []
            principal_total = Decimal("0")
            principal_lend_total = Decimal("0")
            principal_borrow_total = Decimal("0")
            repaid_total = Decimal("0")
            outstanding_total = Decimal("0")
            nearest_due_date = None

            for debt in card_debts:
                debt_repayments = repayments_by_debt.get(debt.id, [])
                debt_forgivenesses = forgivenesses_by_debt.get(debt.id, [])
                debt_issuances = issuances_by_debt.get(debt.id, [])
                serialized_repayments = [self._serialize_repayment(item) for item in debt_repayments]
                serialized_forgivenesses = [self._serialize_forgiveness(item) for item in debt_forgivenesses]
                serialized_issuances = [self._serialize_issuance(item) for item in debt_issuances]
                debt_repaid = sum((Decimal(item["amount"]) for item in serialized_repayments), Decimal("0"))
                debt_forgiven = sum((Decimal(item["amount"]) for item in serialized_forgivenesses), Decimal("0"))
                debt_outstanding = Decimal(debt.principal) - debt_repaid - debt_forgiven
                debt_item = self._serialize_debt_item(
                    debt=debt,
                    repayments=debt_repayments,
                    forgivenesses=debt_forgivenesses,
                    issuances=debt_issuances,
                    latest_rate_map=latest_rate_map,
                )
                cp_match = bool(query_token and self._matches_search_token(cp.name, query_token))
                debt_match = bool(query_token and self._debt_matches_query(debt_item, query_token))
                if query_token and not (cp_match or debt_match):
                    continue

                principal_total += Decimal(debt_item["current_base_principal"])
                if debt.direction == "lend":
                    principal_lend_total += Decimal(debt_item["current_base_principal"])
                else:
                    principal_borrow_total += Decimal(debt_item["current_base_principal"])
                repaid_total += Decimal(debt_item["current_base_repaid_total"])
                outstanding_total += Decimal(debt_item["current_base_outstanding_total"])
                if debt_outstanding > 0 and debt.due_date:
                    if nearest_due_date is None or debt.due_date < nearest_due_date:
                        nearest_due_date = debt.due_date
                debt_items.append(debt_item)

            if not debt_items:
                continue

            status = "active" if outstanding_total > 0 else "closed"
            if not include_closed and status == "closed":
                continue

            cards.append(
                {
                    "counterparty_id": cp.id,
                    "counterparty": cp.name,
                    "principal_total": principal_total,
                    "principal_lend_total": principal_lend_total,
                    "principal_borrow_total": principal_borrow_total,
                    "repaid_total": repaid_total,
                    "outstanding_total": outstanding_total,
                    "base_currency": base_currency,
                    "status": status,
                    "nearest_due_date": nearest_due_date,
                    "debts": debt_items,
                }
            )

        cards.sort(
            key=lambda item: (
                0 if item["status"] == "active" else 1,
                item["nearest_due_date"] is None,
                item["nearest_due_date"] or date.max,
                item["counterparty"].casefold(),
            )
        )
        set_json(
            cache_key,
            {"items": cards},
            ttl_seconds=get_namespace_ttl_seconds("debts"),
        )
        return cards

    def summary_active_totals_current_base(self, *, user_id: int) -> tuple[Decimal, Decimal, int]:
        cards = self.list_cards(user_id=user_id, include_closed=False, q=None)
        lend_total = Decimal("0")
        borrow_total = Decimal("0")
        active_cards = 0
        for card in cards:
            card_has_active = False
            for debt in card.get("debts", []):
                outstanding = Decimal(debt.get("current_base_outstanding_total") or 0)
                if outstanding <= 0:
                    continue
                card_has_active = True
                if debt.get("direction") == "lend":
                    lend_total += outstanding
                else:
                    borrow_total += outstanding
            if card_has_active:
                active_cards += 1
        return lend_total, borrow_total, active_cards

    def list_dashboard_preview_cards(self, *, user_id: int, limit_cards: int = 6) -> list[dict]:
        cards = self.list_cards(user_id=user_id, include_closed=False, q=None)
        return cards[:limit_cards]

    def _resolve_live_base_amount(
        self,
        *,
        amount: Decimal,
        currency: str,
        base_currency: str,
        current_rate,
    ) -> Decimal:
        if currency == base_currency:
            return self.operation_service._money(amount)
        if current_rate is None:
            return self.operation_service._money(0)
        return self.operation_service._money(Decimal(amount) * Decimal(current_rate))

    def _serialize_debt_item(self, *, debt, repayments: list, forgivenesses: list, issuances: list, latest_rate_map: dict) -> dict:
        currency = str(getattr(debt, "currency", "BYN") or "BYN").upper()
        base_currency = str(getattr(debt, "base_currency", "BYN") or "BYN").upper()
        original_principal = self.operation_service._money(getattr(debt, "original_principal", debt.principal))
        repaid_total = sum((Decimal(item.amount) for item in repayments), Decimal("0"))
        forgiven_total = sum((Decimal(item.amount) for item in forgivenesses), Decimal("0"))
        outstanding_total = Decimal(original_principal) - repaid_total - forgiven_total
        rate_row = latest_rate_map.get(currency) if currency != base_currency else None
        current_rate = Decimal(rate_row.rate) if rate_row is not None else None
        return {
            "id": debt.id,
            "counterparty_id": debt.counterparty_id,
            "direction": debt.direction,
            "principal": original_principal,
            "original_principal": original_principal,
            "currency": currency,
            "base_currency": base_currency,
            "closure_reason": getattr(debt, "closure_reason", None),
            "current_rate": current_rate,
            "current_rate_date": rate_row.rate_date if rate_row is not None else None,
            "current_base_principal": self._resolve_live_base_amount(
                amount=original_principal,
                currency=currency,
                base_currency=base_currency,
                current_rate=current_rate,
            ),
            "repaid_total": self.operation_service._money(repaid_total),
            "current_base_repaid_total": self._resolve_live_base_amount(
                amount=self.operation_service._money(repaid_total),
                currency=currency,
                base_currency=base_currency,
                current_rate=current_rate,
            ),
            "forgiven_total": self.operation_service._money(forgiven_total),
            "current_base_forgiven_total": self._resolve_live_base_amount(
                amount=self.operation_service._money(forgiven_total),
                currency=currency,
                base_currency=base_currency,
                current_rate=current_rate,
            ),
            "outstanding_total": self.operation_service._money(outstanding_total),
            "current_base_outstanding_total": self._resolve_live_base_amount(
                amount=self.operation_service._money(outstanding_total),
                currency=currency,
                base_currency=base_currency,
                current_rate=current_rate,
            ),
            "start_date": debt.start_date,
            "due_date": debt.due_date,
            "note": debt.note,
            "created_at": debt.created_at,
            "repayments": [
                {
                    **self._serialize_repayment(item),
                    "currency": currency,
                    "base_currency": base_currency,
                    "current_base_amount": self._resolve_live_base_amount(
                        amount=Decimal(item.amount),
                        currency=currency,
                        base_currency=base_currency,
                        current_rate=current_rate,
                    ),
                }
                for item in repayments
            ],
            "forgivenesses": [
                {
                    **self._serialize_forgiveness(item),
                    "currency": currency,
                    "base_currency": base_currency,
                    "current_base_amount": self._resolve_live_base_amount(
                        amount=Decimal(item.amount),
                        currency=currency,
                        base_currency=base_currency,
                        current_rate=current_rate,
                    ),
                }
                for item in forgivenesses
            ],
            "issuances": [
                {
                    **self._serialize_issuance(item),
                    "currency": currency,
                    "base_currency": base_currency,
                    "current_base_amount": self._resolve_live_base_amount(
                        amount=Decimal(item.amount),
                        currency=currency,
                        base_currency=base_currency,
                        current_rate=current_rate,
                    ),
                }
                for item in issuances
            ],
        }
