"""Local worker progress, without credentials, message contents or DB access."""
from __future__ import annotations

import json
import os
from pathlib import Path
from time import time


HEALTH_PATH = Path("/tmp/financialassistant-bot-health.json")


class WorkerHealth:
    def __init__(self, path: Path = HEALTH_PATH):
        self.path = path
        self.state = {"pid": os.getpid(), "started_at": time(), "last_poll_at": None}

    def tick(self, *, poll_succeeded: bool = False) -> None:
        now = time()
        self.state["progress_at"] = now
        if poll_succeeded:
            self.state["last_poll_at"] = now
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as output:
            os.chmod(temp, 0o600)
            json.dump(self.state, output)
        temp.replace(self.path)


def check_worker_health(path: Path = HEALTH_PATH, *, max_age_seconds: float = 300, now: float | None = None) -> bool:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            return False
        current = time() if now is None else now
        # Progress alone cannot hide a worker repeatedly failing to poll.
        for field in ("progress_at", "last_poll_at"):
            timestamp = state.get(field)
            if not isinstance(timestamp, (int, float)) or not 0 <= current - timestamp <= max_age_seconds:
                return False
        os.kill(int(state["pid"]), 0)
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False
