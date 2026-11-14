from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def timezone_from_preferences(preferences: dict | None) -> tzinfo:
    ui = preferences.get("ui") if isinstance(preferences, dict) else None
    if not isinstance(ui, dict):
        return timezone.utc
    name = str(ui.get("timezone") or "").strip()
    if not name or name == "auto":
        name = str(ui.get("browser_timezone") or "").strip()
    try:
        return ZoneInfo(name) if name else timezone.utc
    except (ValueError, ZoneInfoNotFoundError):
        return timezone.utc


def local_date(timestamp: datetime, user_timezone: tzinfo) -> date:
    # SQLite returns stored UTC timestamps without their timezone.
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(user_timezone).date()
