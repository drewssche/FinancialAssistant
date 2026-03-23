from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.logging import log_background_job_event
from app.repositories.debt_repo import DebtRepository


class DebtReminderService:
    EVENT_TYPE_DUE_SOON = "due_soon"
    EVENT_TYPE_OVERDUE = "overdue"

    def __init__(self, db: Session):
        self.db = db
        self.repo = DebtRepository(db)

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def sync_debt_job(self, *, user_id: int, debt_id: int) -> None:
        debt = self.repo.get_debt_by_id_for_user(user_id=user_id, debt_id=debt_id)
        now_utc = self._now_utc()
        for event_type in (self.EVENT_TYPE_DUE_SOON, self.EVENT_TYPE_OVERDUE):
            self.repo.cancel_pending_reminder_jobs(
                user_id=user_id,
                debt_id=debt_id,
                event_type=event_type,
                canceled_at=now_utc,
            )
        if not debt or not debt.due_date:
            self.db.commit()
            log_background_job_event(
                "debt_reminder",
                "debt_sync_skipped",
                user_id=user_id,
                debt_id=debt_id,
                reason="missing_or_no_due_date",
            )
            return

        if self.repo.repayment_total_for_debt(debt_id=debt_id) >= debt.principal:
            self.db.commit()
            log_background_job_event(
                "debt_reminder",
                "debt_sync_skipped",
                user_id=user_id,
                debt_id=debt_id,
                reason="closed_debt",
            )
            return

        config = self._get_user_reminder_config(user_id=user_id)
        if not config["enabled"]:
            self.db.commit()
            log_background_job_event(
                "debt_reminder",
                "debt_sync_skipped",
                user_id=user_id,
                debt_id=debt_id,
                reason="reminders_disabled",
            )
            return

        due_soon_scheduled_for = self._compute_due_soon_reminder_at(
            due_date=debt.due_date,
            reminder_time=config["time"],
            user_tz=config["timezone"],
            now_utc=now_utc,
        )
        overdue_scheduled_for = self._compute_overdue_reminder_at(
            user_id=user_id,
            debt_id=debt_id,
            due_date=debt.due_date,
            reminder_time=config["time"],
            user_tz=config["timezone"],
            now_utc=now_utc,
        )
        created_jobs = 0
        if due_soon_scheduled_for:
            self.repo.create_reminder_job(
                user_id=user_id,
                debt_id=debt_id,
                event_type=self.EVENT_TYPE_DUE_SOON,
                scheduled_for=due_soon_scheduled_for,
            )
            created_jobs += 1
            log_background_job_event(
                "debt_reminder",
                "debt_job_synced",
                user_id=user_id,
                debt_id=debt_id,
                event_type=self.EVENT_TYPE_DUE_SOON,
                scheduled_for=due_soon_scheduled_for.isoformat(),
            )
        if overdue_scheduled_for:
            self.repo.create_reminder_job(
                user_id=user_id,
                debt_id=debt_id,
                event_type=self.EVENT_TYPE_OVERDUE,
                scheduled_for=overdue_scheduled_for,
            )
            created_jobs += 1
            log_background_job_event(
                "debt_reminder",
                "debt_job_synced",
                user_id=user_id,
                debt_id=debt_id,
                event_type=self.EVENT_TYPE_OVERDUE,
                scheduled_for=overdue_scheduled_for.isoformat(),
            )
        self.db.commit()
        if created_jobs == 0:
            log_background_job_event(
                "debt_reminder",
                "debt_sync_skipped",
                user_id=user_id,
                debt_id=debt_id,
                reason="no_due_soon_or_overdue_job",
                due_date=debt.due_date.isoformat(),
            )

    def sync_user_jobs(self, *, user_id: int) -> None:
        debts = self.repo.list_active_due_dated_debts_for_user(user_id=user_id)
        for debt in debts:
            self.sync_debt_job(user_id=user_id, debt_id=int(debt.id))
        log_background_job_event(
            "debt_reminder",
            "user_jobs_synced",
            user_id=user_id,
            active_due_dated_debt_count=len(debts),
        )

    def list_due_jobs(self) -> list[dict]:
        now_utc = self._now_utc()
        rows = self.repo.list_due_reminder_jobs(now_utc=now_utc)
        jobs: list[dict] = []
        for job, debt, counterparty, identity, preference in rows:
            if not identity or job.event_type not in {self.EVENT_TYPE_DUE_SOON, self.EVENT_TYPE_OVERDUE}:
                continue
            outstanding_total = debt.principal - self.repo.repayment_total_for_debt(debt_id=int(debt.id))
            if outstanding_total <= 0:
                continue
            prefs = preference.data if preference and isinstance(preference.data, dict) else {}
            config = self._get_user_reminder_config_from_prefs(user_id=int(debt.user_id), prefs=prefs)
            if not config["enabled"]:
                continue
            jobs.append(
                {
                    "job": job,
                    "debt": debt,
                    "counterparty": counterparty,
                    "chat_id": str(identity.provider_user_id),
                    "config": config,
                    "outstanding_total": outstanding_total,
                    "event_type": job.event_type,
                }
            )
        return jobs

    def refresh_due_job_payload(self, payload: dict) -> dict | None:
        job = payload.get("job")
        if not job:
            return None
        row = self.repo.get_pending_reminder_job_snapshot(job_id=int(job.id))
        if not row:
            return None
        current_job, debt, counterparty, identity, preference = row
        outstanding_total = debt.principal - self.repo.repayment_total_for_debt(debt_id=int(debt.id))
        if not debt or not debt.due_date or outstanding_total <= 0:
            return None
        prefs = preference.data if preference and isinstance(preference.data, dict) else {}
        config = self._get_user_reminder_config_from_prefs(user_id=int(debt.user_id), prefs=prefs)
        if not config["enabled"] or not identity:
            return None
        return {
            "job": current_job,
            "debt": debt,
            "counterparty": counterparty,
            "chat_id": str(identity.provider_user_id),
            "config": config,
            "outstanding_total": outstanding_total,
            "event_type": current_job.event_type,
        }

    def mark_job_sent(self, payload: dict) -> None:
        refreshed = self.refresh_due_job_payload(payload)
        if not refreshed:
            return
        job = refreshed["job"]
        debt = refreshed["debt"]
        event_type = str(refreshed.get("event_type") or job.event_type or self.EVENT_TYPE_DUE_SOON)
        config = refreshed.get("config") or {}
        now_utc = self._now_utc()
        self.repo.mark_reminder_job_sent(job, sent_at=now_utc)
        if event_type == self.EVENT_TYPE_OVERDUE and debt.due_date:
            next_scheduled_for = self._compute_next_overdue_after_send(
                reminder_time=config["time"],
                user_tz=config["timezone"],
                now_utc=now_utc,
            )
            self.repo.create_reminder_job(
                user_id=int(debt.user_id),
                debt_id=int(debt.id),
                event_type=self.EVENT_TYPE_OVERDUE,
                scheduled_for=next_scheduled_for,
            )
        self.db.commit()
        log_background_job_event(
            "debt_reminder",
            "job_sent",
            user_id=int(debt.user_id),
            debt_id=int(debt.id),
            job_id=int(job.id),
            event_type=event_type,
        )
        if event_type == self.EVENT_TYPE_OVERDUE:
            log_background_job_event(
                "debt_reminder",
                "job_rescheduled",
                user_id=int(debt.user_id),
                debt_id=int(debt.id),
                event_type=event_type,
                next_scheduled_for=next_scheduled_for.isoformat(),
            )

    def build_reminder_text(self, payload: dict) -> str:
        debt = payload.get("debt")
        counterparty = payload.get("counterparty")
        outstanding_total = payload.get("outstanding_total")
        if not debt:
            return "Скоро срок долга"
        direction_label = "Вам нужно вернуть" if debt.direction == "borrow" else "Вам должны вернуть"
        counterparty_name = counterparty.name if counterparty else "—"
        event_type = payload.get("event_type") or self.EVENT_TYPE_DUE_SOON
        title = "Срок долга наступил" if event_type == self.EVENT_TYPE_OVERDUE else "Скоро срок долга"
        return (
            f"{title}\n\n"
            f"{direction_label}\n"
            f"Контрагент: {counterparty_name}\n"
            f"Сумма: {outstanding_total if outstanding_total is not None else debt.principal}\n"
            f"Срок: {debt.due_date.isoformat()}"
        )

    def _get_user_reminder_config(self, *, user_id: int) -> dict:
        preference = self.repo.get_user_preferences(user_id=user_id)
        prefs = preference.data if preference and isinstance(preference.data, dict) else {}
        return self._get_user_reminder_config_from_prefs(user_id=user_id, prefs=prefs)

    def _get_user_reminder_config_from_prefs(self, *, user_id: int, prefs: dict) -> dict:
        plans_prefs = prefs.get("plans") if isinstance(prefs.get("plans"), dict) else {}
        ui_prefs = prefs.get("ui") if isinstance(prefs.get("ui"), dict) else {}
        enabled = plans_prefs.get("reminders_enabled", True) is not False
        timezone_name = ui_prefs.get("timezone", "auto")
        browser_timezone = ui_prefs.get("browser_timezone")
        user_tz = self._resolve_timezone(timezone_name, browser_timezone)
        reminder_time = self._parse_reminder_time(plans_prefs.get("reminder_time"))
        return {
            "user_id": user_id,
            "enabled": enabled,
            "timezone": user_tz,
            "time": reminder_time,
        }

    def _compute_due_soon_reminder_at(self, *, due_date, reminder_time: time, user_tz, now_utc: datetime):
        now_local = now_utc.astimezone(user_tz)
        if due_date <= now_local.date():
            return None
        target_day = due_date - timedelta(days=1)
        target_local = datetime.combine(target_day, reminder_time, tzinfo=user_tz)
        if target_day < now_local.date():
            return None
        if target_day == now_local.date() and target_local <= now_local:
            return (now_utc + timedelta(minutes=1)).replace(second=0, microsecond=0)
        return target_local.astimezone(timezone.utc)

    def _compute_overdue_reminder_at(
        self,
        *,
        user_id: int,
        debt_id: int,
        due_date,
        reminder_time: time,
        user_tz,
        now_utc: datetime,
    ):
        now_local = now_utc.astimezone(user_tz)
        if due_date >= now_local.date():
            return None
        last_job = self.repo.get_latest_sent_reminder_job(
            user_id=user_id,
            debt_id=debt_id,
            event_type=self.EVENT_TYPE_OVERDUE,
        )
        if last_job and last_job.sent_at:
            sent_at = (
                last_job.sent_at.replace(tzinfo=timezone.utc)
                if last_job.sent_at.tzinfo is None
                else last_job.sent_at.astimezone(timezone.utc)
            )
            if sent_at.astimezone(user_tz).date() == now_local.date():
                target_local = datetime.combine(now_local.date() + timedelta(days=1), reminder_time, tzinfo=user_tz)
                return target_local.astimezone(timezone.utc)
        target_local = datetime.combine(now_local.date(), reminder_time, tzinfo=user_tz)
        if target_local <= now_local:
            return (now_utc + timedelta(minutes=1)).replace(second=0, microsecond=0)
        return target_local.astimezone(timezone.utc)

    @staticmethod
    def _compute_next_overdue_after_send(*, reminder_time: time, user_tz, now_utc: datetime):
        now_local = now_utc.astimezone(user_tz)
        target_local = datetime.combine(now_local.date() + timedelta(days=1), reminder_time, tzinfo=user_tz)
        return target_local.astimezone(timezone.utc)

    @staticmethod
    def _resolve_timezone(timezone_name: str | None, browser_timezone: str | None = None):
        normalized = str(timezone_name or "auto").strip()
        if not normalized or normalized == "auto":
            browser_normalized = str(browser_timezone or "").strip()
            if browser_normalized:
                try:
                    return ZoneInfo(browser_normalized)
                except Exception:
                    return timezone.utc
            return timezone.utc
        try:
            return ZoneInfo(normalized)
        except Exception:
            return timezone.utc

    @staticmethod
    def _parse_reminder_time(value: str | None) -> time:
        raw = str(value or "09:00").strip()
        try:
            hours_text, minutes_text = raw.split(":", 1)
            return time(hour=max(0, min(23, int(hours_text))), minute=max(0, min(59, int(minutes_text))))
        except Exception:
            return time(9, 0)
