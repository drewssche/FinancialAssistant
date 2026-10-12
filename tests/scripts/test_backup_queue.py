from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
from time import time
from io import BytesIO
from unittest.mock import Mock

import pytest

from scripts import backup_queue as backup
from scripts.check_backup_health import check_backup_health


@pytest.fixture
def spool(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_REMOTE_DIR", "test:backups")
    monkeypatch.setenv("POSTGRES_USER", "test")
    monkeypatch.setenv("POSTGRES_DB", "test")
    monkeypatch.setenv("BACKUP_ENCRYPTION_PASSWORD_FILE", str(tmp_path / "password"))
    monkeypatch.setattr(backup.subprocess, "Popen", lambda *args, **kwargs: Mock(
        stdout=BytesIO(b"PGDMP private content"), returncode=0,
        wait=Mock(return_value=0), poll=Mock(return_value=0),
    ))
    return tmp_path


def commands(*, fail_upload=False, fail_retention=False, fail_dump=False):
    def run(args, **kwargs):
        if args[0] == "docker":
            if fail_dump:
                raise subprocess.CalledProcessError(1, "docker")
            kwargs["stdout"].write(b"PGDMP private content")
        elif args[0] == "openssl":
            Path(args[args.index("-out") + 1]).write_bytes(b"encrypted" * 8)
        elif args[:2] == ["rclone", "copyto"] and fail_upload:
            raise subprocess.CalledProcessError(1, "rclone")
        elif args[:2] == ["rclone", "delete"] and fail_retention:
            raise subprocess.CalledProcessError(1, "rclone")
    return run


def test_failed_upload_retains_encrypted_copy_then_retries(spool, monkeypatch):
    monkeypatch.setattr(backup, "run_command", commands(fail_upload=True))
    assert backup.backup(spool) == 1
    pending = backup.archives(spool)
    assert len(pending) == 1
    assert pending[0].read_bytes() == b"encrypted" * 8
    assert not list(spool.glob(".creating-*"))
    assert not (spool / "last-upload.json").exists()
    monkeypatch.setattr(backup, "run_command", commands())
    assert backup.backup(spool) == 0
    assert backup.archives(spool) == []
    status = json.loads((spool / "last-run.json").read_text())
    assert status["uploaded_count"] == 2
    assert check_backup_health(spool)[0]


def test_retention_failure_does_not_hide_uploaded_backup(spool, monkeypatch):
    monkeypatch.setattr(backup, "run_command", commands(fail_retention=True))
    assert backup.backup(spool) == 1
    status = json.loads((spool / "last-run.json").read_text())
    assert status["upload"] == "ok"
    assert status["retention"] == "failed"
    assert (spool / "last-upload.json").exists()
    assert check_backup_health(spool) == (False, "external_backup=recent retention=failed")


def test_failed_dump_keeps_existing_queue_and_removes_plaintext(spool, monkeypatch):
    old = spool / "financialassistant-20261010T040000Z.dump.enc"
    old.write_bytes(b"previous encrypted")
    monkeypatch.setattr(backup, "run_command", commands(fail_dump=True))
    monkeypatch.setattr(backup.subprocess, "Popen", lambda *args, **kwargs: Mock(
        stdout=BytesIO(b"partial dump"), returncode=1,
        wait=Mock(return_value=1), poll=Mock(return_value=1),
    ))
    assert backup.backup(spool) == 1
    assert old.read_bytes() == b"previous encrypted"
    assert not list(spool.glob(".creating-*"))


def test_queue_limits_remove_oldest_and_preserve_newest(spool):
    for index in range(3):
        (spool / f"financialassistant-2026101{index}T040000Z.dump.enc").write_bytes(b"0123456789")
    assert backup.trim_queue(spool, max_bytes=20, max_age_days=7) == 1
    files = backup.archives(spool)
    os.utime(files[0], (time() - 8 * 86400, time() - 8 * 86400))
    assert backup.trim_queue(spool, max_bytes=20, max_age_days=7) == 1
    assert backup.archives(spool)[0].name.endswith("12T040000Z.dump.enc")


def test_fresh_upload_of_old_snapshot_is_still_stale(spool):
    backup.atomic_json(spool / "last-upload.json", {"object": "financialassistant-20261010T040000Z.dump.enc", "uploaded_at": time()})
    healthy, message = check_backup_health(spool, now=datetime(2026, 10, 12, tzinfo=timezone.utc))
    assert not healthy
    assert "stale" in message


def test_remote_failure_reason_does_not_expose_stderr():
    error = subprocess.CalledProcessError(1, "rclone", stderr=b"private remote: 410 Gone token=secret")
    assert backup.failure_reason(error) == "http_410"
