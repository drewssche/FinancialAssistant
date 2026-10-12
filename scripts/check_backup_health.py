"""Read local evidence of external backup freshness; never contacts storage."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def check_backup_health(spool: Path, *, max_age_hours: float = 36, now: datetime | None = None) -> tuple[bool, str]:
    try:
        upload = json.loads((spool / "last-upload.json").read_text())
        name = upload["object"]
        stamp = name.removeprefix("financialassistant-").removesuffix(".dump.enc")
        fmt = "%Y%m%dT%H%M%S%fZ" if len(stamp) > 16 else "%Y%m%dT%H%M%SZ"
        created = datetime.strptime(stamp, fmt).replace(tzinfo=timezone.utc)
        age = ((now or datetime.now(timezone.utc)) - created).total_seconds() / 3600
        if not 0 <= age <= max_age_hours:
            return False, f"external_backup=stale snapshot_age_hours={age:.1f}"
        run = json.loads((spool / "last-run.json").read_text())
        if run.get("creation") != "ok" or run.get("upload") != "ok":
            return False, "external_backup=recent last_run=failed"
        if run.get("retention") == "failed":
            return False, "external_backup=recent retention=failed"
        return True, f"external_backup=recent snapshot_age_hours={age:.1f} restore=not_checked"
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False, "external_backup=unknown missing_or_invalid_status"


if __name__ == "__main__":
    healthy, message = check_backup_health(
        Path(os.environ.get("BACKUP_SPOOL_DIR", "/var/lib/financialassistant-backups")),
        max_age_hours=float(os.environ.get("BACKUP_MAX_AGE_HOURS", "36")),
    )
    print(message)
    raise SystemExit(0 if healthy else 1)
