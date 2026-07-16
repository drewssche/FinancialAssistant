from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.plan_reminder_service import PlanReminderService


@dataclass(frozen=True)
class TelegramPlanReminderDelivery:
    chat_id: str
    text: str
    reply_markup: dict | None
    user_id: int
    plan_id: int
    payload: dict


class TelegramPlanReminderBotService:
    def __init__(self, db: Session):
        self.reminder_service = PlanReminderService(db)

    def list_due_deliveries(self) -> list[TelegramPlanReminderDelivery]:
        deliveries: list[TelegramPlanReminderDelivery] = []
        for payload in self.reminder_service.list_due_jobs():
            refreshed = self.reminder_service.refresh_due_job_payload(payload)
            if not refreshed or not refreshed.get("chat_id"):
                continue
            plan = refreshed.get("plan")
            if not plan:
                continue
            deliveries.append(
                TelegramPlanReminderDelivery(
                    chat_id=str(refreshed["chat_id"]),
                    text=self.reminder_service.build_reminder_text(refreshed),
                    reply_markup=self.reminder_service.build_reminder_reply_markup(refreshed),
                    user_id=int(plan.user_id),
                    plan_id=int(plan.id),
                    payload=refreshed,
                )
            )
        return deliveries

    def mark_delivery_sent(self, delivery: TelegramPlanReminderDelivery) -> None:
        self.reminder_service.mark_job_sent(delivery.payload)

    def claim_delivery(self, delivery: TelegramPlanReminderDelivery) -> TelegramPlanReminderDelivery | None:
        payload = self.reminder_service.claim_job(delivery.payload)
        if payload is None:
            return None
        return TelegramPlanReminderDelivery(
            chat_id=str(payload["chat_id"]),
            text=self.reminder_service.build_reminder_text(payload),
            reply_markup=self.reminder_service.build_reminder_reply_markup(payload),
            user_id=delivery.user_id,
            plan_id=delivery.plan_id,
            payload=payload,
        )

    def release_delivery(self, delivery: TelegramPlanReminderDelivery) -> None:
        self.reminder_service.release_job(delivery.payload)
