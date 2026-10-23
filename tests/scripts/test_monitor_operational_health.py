import json
from types import SimpleNamespace
from scripts import monitor_operational_health as monitor


def test_inspect_is_narrow_and_does_not_fetch_secrets(monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(stdout='"abc" 4 "running" "healthy"')
    monkeypatch.setattr(monitor.subprocess, 'run', run)
    assert monitor.bot_status() == {'id': 'abc', 'restarts': 4, 'healthy': True}
    assert '.Config' not in str(calls) and '--format' in calls[0]


def test_docker_failure_reports_unhealthy(monkeypatch):
    monkeypatch.setattr(monitor.subprocess, 'run', lambda *a, **kw: (_ for _ in ()).throw(OSError()))
    assert monitor.bot_status()['healthy'] is False


def test_backup_states(monkeypatch, tmp_path):
    for result, expected in [((True, 'external_backup=recent'), 'ok'),
        ((False, 'external_backup=stale'), 'stale'),
        ((False, 'external_backup=unknown'), 'unknown'),
        ((False, 'external_backup=recent last_run=failed'), 'failed'),
        ((False, 'external_backup=recent retention=failed'), 'retention')]:
        monkeypatch.setattr(monitor, 'check_backup_health', lambda p: result)
        assert monitor.backup_status(tmp_path) == expected
