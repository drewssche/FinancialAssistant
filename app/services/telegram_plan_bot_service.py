from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import log_telegram_plan_event
from app.repositories.user_repo import UserRepository
from app.services.bank_currency_rate_registry import BANK_RATE_PROVIDERS
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
            if str(exc) in {
                "Plan is already completed",
                "This recurring plan occurrence is already confirmed today",
            }:
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
        currency = str(operation.get("currency") or operation.get("base_currency") or "BYN").upper()
        base_currency = str(operation.get("base_currency") or currency).upper()
        if currency != base_currency:
            amount_text = (
                f"{operation['original_amount']} {currency} → "
                f"{operation['amount']} {base_currency}"
            )
        else:
            amount_text = f"{operation['amount']} {base_currency}"
        lines = [
            "План подтвержден",
            f"• Операция {amount_text} на {operation['operation_date']}",
        ]
        if currency != base_currency:
            source = operation.get("fx_rate_source")
            if source == "bank":
                bank_code = str(operation.get("fx_bank_code") or "")
                bank_name = str(
                    operation.get("fx_bank_name")
                    or BANK_RATE_PROVIDERS.get(bank_code, {}).get("name")
                    or bank_code
                )
                rate_kind = (
                    "покупка банком"
                    if operation.get("fx_rate_kind") == "buy"
                    else "продажа банком"
                )
                channel = str(
                    BANK_RATE_PROVIDERS.get(bank_code, {}).get("channel_label")
                    or operation.get("fx_bank_channel")
                    or ""
                )
                provider = " · ".join(value for value in (bank_name, rate_kind, channel) if value)
            elif source == "nbrb":
                provider = "НБРБ"
            else:
                provider = "Ручной курс"
            stale = " · котировка устарела" if operation.get("fx_rate_stale") else ""
            lines.append(
                f"• Курс: {provider} · {operation.get('fx_rate_display')} {base_currency} "
                f"за {operation.get('fx_rate_scale') or 1} {currency}{stale}"
            )
        if plan.get("note"):
            lines.append(plan["note"])
        return TelegramPlanConfirmResult(
            message_text="\n".join(lines),
            callback_text="Подтверждено",
        )
