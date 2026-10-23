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


def test_health_requires_live_process(tmp_path):
    path = tmp_path / "health.json"
    worker = WorkerHealth(path)
    worker.state["pid"] = 2147483647
    worker.tick(poll_succeeded=True)
    assert not check_worker_health(path)


def test_stdlib_only_probe_reports_fresh_stale_and_missing_state(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    path = tmp_path / "health.json"
    marker = tmp_path / "site-loaded"
    (tmp_path / "sitecustomize.py").write_text(
        f"from pathlib import Path; Path({str(marker)!r}).touch()\n"
    )
    runner = """
import runpy, sys
from pathlib import Path
from app.core import worker_health
original = worker_health.check_worker_health
worker_health.check_worker_health = lambda: original(Path(sys.argv[1]))
runpy.run_path(sys.argv[2], run_name='__main__')
"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": os.pathsep.join([str(tmp_path), str(root)])}
    worker = WorkerHealth(path)
    for state, expected in [("fresh", 0), ("stale_poll", 1), ("stale_progress", 1), ("missing", 1)]:
        worker.tick(poll_succeeded=True)
        if state.startswith("stale"):
            field = "last_poll_at" if state == "stale_poll" else "progress_at"
            data = json.loads(path.read_text())
            data[field] = time() - 301
            path.write_text(json.dumps(data))
        elif state == "missing":
            path.unlink()
        result = subprocess.run(
            [sys.executable, "-S", "-c", runner, str(path), str(root / "scripts/check_telegram_bot_health.py")],
            cwd=root, env=env, capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == expected, result.stderr
        assert ("telegram worker: healthy" if expected == 0 else "no recent successful poll/progress") in result.stdout
        assert not marker.exists()
