from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.repositories.plan_repo import PlanRepository


class PlanReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PlanRepository(db)

    def collect_due_reminders(self) -> list[dict]:
        results: list[dict] = []
        for identity, preference in self.repo.list_user_plan_reminder_targets():
            prefs = preference.data if preference and isinstance(preference.data, dict) else {}
            plans_prefs = prefs.get("plans") if isinstance(prefs.get("plans"), dict) else {}
            if plans_prefs.get("reminders_enabled", True) is False:
                continue
            timezone_name = ((prefs.get("ui") or {}) if isinstance(prefs.get("ui"), dict) else {}).get("timezone", "auto")
            user_tz = self._resolve_timezone(timezone_name)
            now_local = datetime.now(user_tz)
            today_local = now_local.date()
            due_items = []
            overdue_items = []
            for plan in self.repo.list_active_plans_for_user(user_id=int(identity.user_id)):
                if plan.scheduled_date > today_local:
                    continue
                reminded_today = False
                if plan.last_reminded_at:
                    reminded_local = plan.last_reminded_at.astimezone(user_tz).date()
                    reminded_today = reminded_local == today_local
                if reminded_today:
                    continue
                bucket = overdue_items if plan.scheduled_date < today_local else due_items
                bucket.append(plan)
            if not due_items and not overdue_items:
                continue
            results.append(
                {
                    "user_id": int(identity.user_id),
                    "chat_id": str(identity.provider_user_id),
                    "username": identity.username,
                    "today": today_local,
                    "timezone": str(user_tz),
                    "due_items": due_items,
                    "overdue_items": overdue_items,
                }
            )
        return results

    def mark_reminded_items(self, items: list) -> None:
        if not items:
            return
        now = datetime.now(timezone.utc)
        for item in items:
            self.repo.create_event(
                user_id=int(item.user_id),
                plan_id=int(item.id),
                operation_id=None,
                event_type="reminded",
                kind=item.kind,
                amount=item.amount,
                effective_date=item.scheduled_date,
                note=item.note,
                category_name=self.repo.get_category_name(category_id=item.category_id),
            )
            item.last_reminded_at = now
            item.reminder_sent_count = int(item.reminder_sent_count or 0) + 1
        self.db.commit()

    def build_reminder_text(self, payload: dict) -> str:
        due_items = payload.get("due_items") or []
        overdue_items = payload.get("overdue_items") or []
        lines = ["Планы к подтверждению"]
        if overdue_items:
            lines.append("")
            lines.append("Просрочено:")
            for item in overdue_items[:6]:
                lines.append(self._format_item_line(item))
        if due_items:
            lines.append("")
            lines.append("На сегодня:")
            for item in due_items[:6]:
                lines.append(self._format_item_line(item))
        total_hidden = max(0, len(overdue_items) + len(due_items) - 12)
        if total_hidden > 0:
            lines.append("")
            lines.append(f"Еще: {total_hidden}")
        return "\n".join(lines)

    @staticmethod
    def _format_item_line(item) -> str:
        kind_label = "Доход" if item.kind == "income" else "Расход"
        note = f" - {item.note}" if item.note else ""
        return f"• {kind_label} {item.amount} на {item.scheduled_date.isoformat()}{note}"

    @staticmethod
    def _resolve_timezone(timezone_name: str | None):
        normalized = str(timezone_name or "auto").strip()
        if not normalized or normalized == "auto":
            return timezone.utc
        try:
            return ZoneInfo(normalized)
        except Exception:
            return timezone.utc
