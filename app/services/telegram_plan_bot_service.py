from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import log_telegram_plan_event
from app.repositories.user_repo import UserRepository
from app.services.plan_service import PlanService


class TelegramPlanBotServiceError(Exception):
    pass


class TelegramPlanUserNotFoundError(TelegramPlanBotServiceError):
    pass


class TelegramPlanNotFoundError(TelegramPlanBotServiceError):
    pass


class TelegramPlanAlreadyCompletedError(TelegramPlanBotServiceError):
    pass


@dataclass(frozen=True)
class TelegramPlanConfirmResult:
    message_text: str
    callback_text: str


class TelegramPlanBotService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.plan_service = PlanService(db)

    def confirm_plan_from_telegram(self, *, telegram_id: str, plan_id: int) -> TelegramPlanConfirmResult:
        log_telegram_plan_event(
            "confirm_attempted",
            telegram_id=telegram_id,
            plan_id=plan_id,
        )
        user = self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            log_telegram_plan_event(
                "user_not_found",
                telegram_id=telegram_id,
                plan_id=plan_id,
            )
            raise TelegramPlanUserNotFoundError("Пользователь не найден")

        try:
            payload = self.plan_service.confirm_plan(user_id=int(user.id), plan_id=plan_id)
        except LookupError as exc:
            log_telegram_plan_event(
                "plan_not_found",
                telegram_id=telegram_id,
                user_id=int(user.id),
                plan_id=plan_id,
            )
            raise TelegramPlanNotFoundError("План не найден") from exc
        except ValueError as exc:
            if str(exc) == "Plan is already completed":
                log_telegram_plan_event(
                    "already_completed",
                    telegram_id=telegram_id,
                    user_id=int(user.id),
                    plan_id=plan_id,
                )
                raise TelegramPlanAlreadyCompletedError("План уже обработан") from exc
            log_telegram_plan_event(
                "confirm_failed",
                telegram_id=telegram_id,
                user_id=int(user.id),
                plan_id=plan_id,
                reason=str(exc),
            )
            raise TelegramPlanBotServiceError(str(exc)) from exc

        plan = payload["plan"]
        operation = payload["operation"]
        log_telegram_plan_event(
            "confirm_succeeded",
            telegram_id=telegram_id,
            user_id=int(user.id),
            plan_id=plan_id,
            operation_id=operation.get("id"),
        )
        lines = [
            "План подтвержден",
            f"• Операция {operation['amount']} на {operation['operation_date']}",
        ]
        if plan.get("note"):
            lines.append(plan["note"])
        return TelegramPlanConfirmResult(
            message_text="\n".join(lines),
            callback_text="Подтверждено",
        )
