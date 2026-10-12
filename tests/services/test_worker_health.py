import json
from time import time

from app.core.worker_health import WorkerHealth, check_worker_health


def test_worker_needs_successful_poll_and_recent_progress(tmp_path):
    path = tmp_path / "health.json"
    assert not check_worker_health(path)
    worker = WorkerHealth(path)
    worker.tick()
    assert not check_worker_health(path)
    worker.tick(poll_succeeded=True)
    assert check_worker_health(path)
    assert path.stat().st_mode & 0o777 == 0o600
    worker.state["last_poll_at"] = time() - 301
    worker.tick()
    assert not check_worker_health(path)


def test_health_rejects_stale_or_invalid_state(tmp_path):
    path = tmp_path / "health.json"
    worker = WorkerHealth(path)
    worker.tick(poll_succeeded=True)
    assert not check_worker_health(path, now=time() + 301)
    assert not check_worker_health(path, now=time() - 60)
    for data in ["", "broken", json.dumps({"pid": "invalid"})]:
        path.write_text(data)
        assert not check_worker_health(path)
