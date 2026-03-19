from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.repositories.plan_repo import PlanRepository


class PlanReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PlanRepository(db)

    def sync_plan_job(self, plan) -> None:
        if not plan:
            return
        now_utc = datetime.now(timezone.utc)
        self.repo.cancel_pending_reminder_jobs(
            user_id=int(plan.user_id),
            plan_id=int(plan.id),
            canceled_at=now_utc,
        )
        if plan.status != "active":
            return
        config = self._get_user_reminder_config(user_id=int(plan.user_id))
        if not config["enabled"]:
            return
        scheduled_for = self._compute_next_reminder_at(
            scheduled_date=plan.scheduled_date,
            reminder_time=config["time"],
            user_tz=config["timezone"],
            now_utc=now_utc,
            after_send=False,
        )
        self.repo.create_reminder_job(
            user_id=int(plan.user_id),
            plan_id=int(plan.id),
            scheduled_for=scheduled_for,
        )

    def sync_user_jobs(self, *, user_id: int) -> None:
        now_utc = datetime.now(timezone.utc)
        plans = self.repo.list_active_plans_for_user(user_id=user_id)
        config = self._get_user_reminder_config(user_id=user_id)
        for plan in plans:
            self.repo.cancel_pending_reminder_jobs(
                user_id=int(plan.user_id),
                plan_id=int(plan.id),
                canceled_at=now_utc,
            )
            if not config["enabled"]:
                continue
            scheduled_for = self._compute_next_reminder_at(
                scheduled_date=plan.scheduled_date,
                reminder_time=config["time"],
                user_tz=config["timezone"],
                now_utc=now_utc,
                after_send=False,
            )
            self.repo.create_reminder_job(
                user_id=int(plan.user_id),
                plan_id=int(plan.id),
                scheduled_for=scheduled_for,
            )

    def list_due_jobs(self) -> list[dict]:
        now_utc = datetime.now(timezone.utc)
        rows = self.repo.list_due_reminder_jobs(now_utc=now_utc)
        jobs: list[dict] = []
        for job, plan, identity, preference in rows:
            if not identity:
                continue
            prefs = preference.data if preference and isinstance(preference.data, dict) else {}
            config = self._get_user_reminder_config_from_prefs(user_id=int(plan.user_id), prefs=prefs)
            if not config["enabled"]:
                continue
            jobs.append(
                {
                    "job": job,
                    "plan": plan,
                    "chat_id": str(identity.provider_user_id),
                    "config": config,
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
        current_job, plan, identity, preference = row
        if not plan or plan.status != "active":
            return None
        prefs = preference.data if preference and isinstance(preference.data, dict) else {}
        config = self._get_user_reminder_config_from_prefs(user_id=int(plan.user_id), prefs=prefs)
        if not config["enabled"]:
            return None
        return {
            "job": current_job,
            "plan": plan,
            "chat_id": str(identity.provider_user_id) if identity else None,
            "config": config,
        }

    def mark_job_sent(self, payload: dict) -> None:
        job = payload.get("job")
        plan = payload.get("plan")
        config = payload.get("config") or {}
        if not job or not plan:
            return
        refreshed = self.refresh_due_job_payload(payload)
        if not refreshed:
            return
        job = refreshed["job"]
        plan = refreshed["plan"]
        config = refreshed.get("config") or config
        now_utc = datetime.now(timezone.utc)
        self.repo.mark_reminder_job_sent(job, sent_at=now_utc)
        self.repo.create_event(
            user_id=int(plan.user_id),
            plan_id=int(plan.id),
            operation_id=None,
            event_type="reminded",
            kind=plan.kind,
            amount=plan.amount,
            effective_date=plan.scheduled_date,
            note=plan.note,
            category_name=self.repo.get_category_name(category_id=plan.category_id),
        )
        plan.last_reminded_at = now_utc
        plan.reminder_sent_count = int(plan.reminder_sent_count or 0) + 1
        if plan.status == "active" and bool(config.get("enabled", True)):
            next_scheduled_for = self._compute_next_reminder_at(
                scheduled_date=plan.scheduled_date,
                reminder_time=config["time"],
                user_tz=config["timezone"],
                now_utc=now_utc,
                after_send=True,
            )
            self.repo.create_reminder_job(
                user_id=int(plan.user_id),
                plan_id=int(plan.id),
                scheduled_for=next_scheduled_for,
            )
        self.db.commit()

    def build_reminder_text(self, payload: dict) -> str:
        plan = payload.get("plan")
        if not plan:
            return "План к подтверждению"
        kind_label = "Доход" if plan.kind == "income" else "Расход"
        lines = ["План к подтверждению"]
        lines.append(f"• {kind_label} {plan.amount} на {plan.scheduled_date.isoformat()}")
        if plan.note:
            lines.append(plan.note)
        return "\n".join(lines)

    def get_plan_reminder_snapshot(self, *, user_id: int, plan_id: int) -> tuple[datetime | None, str | None]:
        config = self._get_user_reminder_config(user_id=user_id)
        if not config["enabled"]:
            return None, None
        jobs = self.repo.list_next_pending_jobs_for_plans(user_id=user_id, plan_ids=[plan_id])
        job = jobs.get(plan_id)
        if not job:
            return None, None
        reminder_local = job.scheduled_for.astimezone(config["timezone"])
        now_local = datetime.now(config["timezone"])
        if reminder_local.date() == now_local.date() and reminder_local <= now_local + timedelta(minutes=2):
            return job.scheduled_for, "Напоминание скоро"
        return job.scheduled_for, f"Напоминание {reminder_local.strftime('%H:%M')}"

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

    def _compute_next_reminder_at(
        self,
        *,
        scheduled_date: date,
        reminder_time: time,
        user_tz,
        now_utc: datetime,
        after_send: bool,
    ) -> datetime:
        now_local = now_utc.astimezone(user_tz)
        target_day = max(scheduled_date, now_local.date())
        if after_send:
            target_day = max(scheduled_date, now_local.date() + timedelta(days=1))
            return datetime.combine(target_day, reminder_time, tzinfo=user_tz).astimezone(timezone.utc)
        target_local = datetime.combine(target_day, reminder_time, tzinfo=user_tz)
        if scheduled_date <= now_local.date() and target_local <= now_local:
            return (now_utc + timedelta(minutes=1)).replace(second=0, microsecond=0)
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
            hour_str, minute_str = raw.split(":", 1)
            hour = max(0, min(23, int(hour_str)))
            minute = max(0, min(59, int(minute_str)))
            return time(hour=hour, minute=minute)
        except Exception:
            return time(hour=9, minute=0)
