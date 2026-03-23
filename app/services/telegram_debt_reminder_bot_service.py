from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.debt_reminder_service import DebtReminderService


@dataclass(frozen=True)
class TelegramDebtReminderDelivery:
    chat_id: str
    text: str
    user_id: int
    debt_id: int
    payload: dict


class TelegramDebtReminderBotService:
    def __init__(self, db: Session):
        self.reminder_service = DebtReminderService(db)

    def list_due_deliveries(self) -> list[TelegramDebtReminderDelivery]:
        deliveries: list[TelegramDebtReminderDelivery] = []
        for payload in self.reminder_service.list_due_jobs():
            refreshed = self.reminder_service.refresh_due_job_payload(payload)
            if not refreshed or not refreshed.get("chat_id"):
                continue
            debt = refreshed.get("debt")
            if not debt:
                continue
            deliveries.append(
                TelegramDebtReminderDelivery(
                    chat_id=str(refreshed["chat_id"]),
                    text=self.reminder_service.build_reminder_text(refreshed),
                    user_id=int(debt.user_id),
                    debt_id=int(debt.id),
                    payload=refreshed,
                )
            )
        return deliveries

    def mark_delivery_sent(self, delivery: TelegramDebtReminderDelivery) -> None:
        self.reminder_service.mark_job_sent(delivery.payload)
