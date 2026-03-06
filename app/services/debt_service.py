from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.debt_repo import DebtRepository


class DebtService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DebtRepository(db)

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

    def create_debt(
        self,
        user_id: int,
        counterparty: str,
        direction: str,
        principal: Decimal,
        start_date: date,
        due_date: date | None = None,
        note: str | None = None,
    ):
        self._validate_direction(direction)
        self._validate_positive_amount(principal, "principal")
        if due_date and due_date < start_date:
            raise ValueError("due_date must be greater than or equal to start_date")

        normalized_name, name_ci = self._normalize_counterparty_name(counterparty)
        cp = self.repo.get_counterparty_by_name_ci(user_id=user_id, name_ci=name_ci)
        if not cp:
            cp = self.repo.create_counterparty(user_id=user_id, name=normalized_name, name_ci=name_ci)
        merge_target = self.repo.find_active_merge_candidate(
            user_id=user_id,
            counterparty_id=cp.id,
            direction=direction,
        )
        if merge_target:
            updates = {"principal": Decimal(merge_target.principal) + Decimal(principal)}
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
        self.db.refresh(debt)
        return debt, cp

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

        repaid = self.repo.repayment_total_for_debt(debt_id=debt_id)
        principal = Decimal(debt.principal)
        outstanding = principal - repaid
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
            )
            carry_note = note or f"Переплата по долгу #{debt.id}"
            if merge_target:
                updates = {
                    "principal": Decimal(merge_target.principal) + overpay,
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
        self.db.refresh(repayment)
        return repayment

    def get_debt_with_repayments(self, user_id: int, debt_id: int) -> dict:
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")
        repayments = self.repo.list_repayments_for_debts([debt.id])
        issuances = self.repo.list_issuances_for_debts([debt.id])
        repaid_total = sum((Decimal(item.amount) for item in repayments), Decimal("0"))
        outstanding_total = Decimal(debt.principal) - repaid_total
        return {
            "id": debt.id,
            "counterparty_id": debt.counterparty_id,
            "direction": debt.direction,
            "principal": debt.principal,
            "repaid_total": repaid_total,
            "outstanding_total": outstanding_total,
            "start_date": debt.start_date,
            "due_date": debt.due_date,
            "note": debt.note,
            "created_at": debt.created_at,
            "repayments": repayments,
            "issuances": issuances,
        }

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
        repaid = self.repo.repayment_total_for_debt(debt_id=debt_id)
        if Decimal(principal) < repaid:
            raise ValueError("principal must be greater than or equal to repaid total")

        start_date = updates.get("start_date", debt.start_date)
        due_date = updates.get("due_date", debt.due_date)
        if due_date and start_date and due_date < start_date:
            raise ValueError("due_date must be greater than or equal to start_date")

        allowed = {"counterparty_id", "direction", "principal", "start_date", "due_date", "note"}
        payload = {key: value for key, value in updates.items() if key in allowed}
        if payload:
            debt = self.repo.update_debt(debt, payload)
            self.db.commit()
            self.db.refresh(debt)
        return debt

    def delete_debt(self, user_id: int, debt_id: int) -> None:
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        if not debt:
            raise LookupError("Debt not found")
        self.repo.delete_debt(debt)
        self.db.commit()

    def list_cards(self, user_id: int, include_closed: bool = False) -> list[dict]:
        counterparties = self.repo.list_counterparties(user_id=user_id)
        if not counterparties:
            return []

        counterparty_ids = [item.id for item in counterparties]
        debts = self.repo.list_debts_for_counterparties(user_id=user_id, counterparty_ids=counterparty_ids)
        debt_ids = [item.id for item in debts]
        repayments = self.repo.list_repayments_for_debts(debt_ids=debt_ids)
        issuances = self.repo.list_issuances_for_debts(debt_ids=debt_ids)

        repayments_by_debt: dict[int, list] = defaultdict(list)
        for rep in repayments:
            repayments_by_debt[rep.debt_id].append(rep)
        issuances_by_debt: dict[int, list] = defaultdict(list)
        for issuance in issuances:
            issuances_by_debt[issuance.debt_id].append(issuance)

        debts_by_counterparty: dict[int, list] = defaultdict(list)
        for debt in debts:
            debts_by_counterparty[debt.counterparty_id].append(debt)

        cards: list[dict] = []
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
                debt_issuances = issuances_by_debt.get(debt.id, [])
                debt_repaid = sum((Decimal(item.amount) for item in debt_repayments), Decimal("0"))
                debt_outstanding = Decimal(debt.principal) - debt_repaid
                principal_total += Decimal(debt.principal)
                if debt.direction == "lend":
                    principal_lend_total += Decimal(debt.principal)
                else:
                    principal_borrow_total += Decimal(debt.principal)
                repaid_total += debt_repaid
                outstanding_total += debt_outstanding
                if debt_outstanding > 0 and debt.due_date:
                    if nearest_due_date is None or debt.due_date < nearest_due_date:
                        nearest_due_date = debt.due_date

                debt_items.append(
                    {
                        "id": debt.id,
                        "counterparty_id": debt.counterparty_id,
                        "direction": debt.direction,
                        "principal": debt.principal,
                        "repaid_total": debt_repaid,
                        "outstanding_total": debt_outstanding,
                        "start_date": debt.start_date,
                        "due_date": debt.due_date,
                        "note": debt.note,
                        "created_at": debt.created_at,
                        "repayments": debt_repayments,
                        "issuances": debt_issuances,
                    }
                )

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
        return cards
