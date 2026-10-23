"""Encrypted backup queue. Invoked by backup_postgres.sh after loading its env.

Only encrypted archives persist. A failed upload never removes an archive.
No remote/provider credentials or subprocess output are written to status/logs.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from time import time, sleep


PREFIX = "financialassistant-"


def positive_env(name: str, default: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def atomic_json(path: Path, data: dict) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as output:
        temp.chmod(0o600)
        json.dump(data, output, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
    temp.replace(path)


def run_command(args: list[str], *, timeout: int = 300, **kwargs) -> None:
    subprocess.run(args, check=True, timeout=timeout, stderr=subprocess.PIPE, **kwargs)


def failure_reason(exc: Exception) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout"
    # Extract an allowlisted status only; never log rclone stderr/URLs/tokens.
    output = getattr(exc, "stderr", None) or b""
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    match = re.search(r"\b(401|403|404|408|410|429|500|502|503|504)\b", output[:16384])
    return f"http_{match[1]}" if match else type(exc).__name__


def archives(spool: Path) -> list[Path]:
    return sorted(p for p in spool.glob(f"{PREFIX}*.dump.enc") if p.is_file() and not p.is_symlink())


def trim_queue(spool: Path, *, max_bytes: int, max_age_days: int) -> int:
    files = archives(spool)
    size = sum(p.stat().st_size for p in files)
    removed = 0
    # Called only after creating today's archive. Keep the newest at all times;
    # enforce the single-file limit before publishing it into the queue.
    for path in files[:-1]:
        if size <= max_bytes and time() - path.stat().st_mtime <= max_age_days * 86400:
            continue
        size -= path.stat().st_size
        path.unlink()
        removed += 1
    return removed


def create_archive(spool: Path, *, max_bytes: int) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = spool / f"{PREFIX}{stamp}.dump.enc"
    # Stream directly to encryption: no plaintext dump survives a crash.
    # Encryption remains byte-compatible with verify_postgres_restore.sh.
    with tempfile.TemporaryDirectory(prefix=".creating-", dir=spool) as temporary:
        encrypted = Path(temporary) / "database.dump.enc"
        dump = subprocess.Popen([
            "docker", "compose", "exec", "-T", "db", "pg_dump",
            "--username", os.environ["POSTGRES_USER"], "--dbname", os.environ["POSTGRES_DB"],
            "--format", "custom", "--no-owner", "--no-acl",
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            run_command([
                "openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2",
                "-pass", f"file:{os.environ['BACKUP_ENCRYPTION_PASSWORD_FILE']}",
                "-out", str(encrypted),
            ], stdin=dump.stdout, stdout=subprocess.DEVNULL)
            if dump.wait(timeout=30) != 0:
                raise subprocess.CalledProcessError(dump.returncode, "pg_dump")
        finally:
            dump.stdout.close()
            if dump.poll() is None:
                dump.kill()
                dump.wait()
        if not 32 < encrypted.stat().st_size <= max_bytes:
            raise ValueError("Encrypted dump is empty or exceeds configured queue capacity")
        encrypted.chmod(0o600)
        with encrypted.open("rb") as archive:
            os.fsync(archive.fileno())
        encrypted.replace(target)
    return target


def archive_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_remote_archive(path: Path, remote_object: str) -> tuple[bool, str]:
    """A provider can finish PUT after returning 500. Only read-back proves it.

    The download is encrypted, temporary and outside the retry queue. Never
    delete the source based on an HTTP acknowledgement or remote size alone.
    """
    expected = archive_hash(path)
    error = 'readback_hash_mismatch'
    with tempfile.TemporaryDirectory(prefix='.verifying-', dir=path.parent) as directory:
        downloaded = Path(directory) / 'archive.enc'
        for delay in (0, 15, 45):
            if delay:
                sleep(delay)
            try:
                with downloaded.open('wb') as stream:
                    downloaded.chmod(0o600)
                    run_command([
                        'rclone', 'cat', remote_object, '--retries', '1',
                        '--low-level-retries', '1', '--contimeout', '15s', '--timeout', '30s',
                    ], timeout=90, stdout=stream)
            except (subprocess.SubprocessError, OSError) as exc:
                error = failure_reason(exc)
            # A transfer may report a late error after returning the full body.
            if downloaded.exists() and downloaded.stat().st_size == path.stat().st_size:
                if archive_hash(downloaded) == expected:
                    return True, ''
                error = 'readback_hash_mismatch'
    return False, error


def upload_queue(spool: Path, remote: str, status: dict) -> bool:
    # A historical object must not prevent today's snapshot from being uploaded.
    for path in reversed(archives(spool)):
        remote_object = f"{remote.rstrip('/')}/{path.name}"
        upload_error = None
        try:
            run_command([
                "rclone", "copyto", str(path), remote_object,
                "--retries", "1", "--low-level-retries", "1",
                "--contimeout", "15s", "--timeout", "60s",
            ], timeout=180, stdout=subprocess.DEVNULL)
        except (subprocess.SubprocessError, OSError) as exc:
            upload_error = failure_reason(exc)
        verified, verification_error = verify_remote_archive(path, remote_object)
        if not verified:
            status["upload"] = "failed"
            status["upload_error"] = upload_error or verification_error
            status["verification_error"] = verification_error
            status["failed_object"] = path.name
            return False
        if upload_error:
            status['verified_after_upload_error'] = status.get('verified_after_upload_error', 0) + 1
        try:
            previous = json.loads((spool / 'last-upload.json').read_text())
        except (OSError, ValueError):
            previous = {}
        if not isinstance(previous, dict):
            previous = {}
        if path.name >= str(previous.get('object', '')):
            atomic_json(spool / "last-upload.json", {
                "object": path.name, "uploaded_at": time(), "verification": "sha256_readback",
                "sha256": archive_hash(path),
            })
        path.unlink()  # Only after verified read-back and a durable record.
        status["uploaded_count"] += 1
    status["upload"] = "ok"
    return True


def backup(spool: Path) -> int:
    max_bytes = positive_env("BACKUP_SPOOL_MAX_MB", 512) * 1024 * 1024
    max_age = positive_env("BACKUP_SPOOL_MAX_AGE_DAYS", 7)
    retention = positive_env("BACKUP_RETENTION_DAYS", 30)
    remote = os.environ["BACKUP_REMOTE_DIR"]
    if not remote.strip():
        raise ValueError("BACKUP_REMOTE_DIR must not be empty")
    status = {"started_at": time(), "creation": "pending", "upload": "not_run", "retention": "not_run", "uploaded_count": 0}
    exit_code = 1
    try:
        # Keep headroom while creating a new encrypted archive before pruning.
        if shutil.disk_usage(spool).free < 2 * max_bytes + 64 * 1024 * 1024:
            raise ValueError("Insufficient free space for safe backup creation")
        created = create_archive(spool, max_bytes=max_bytes)
        status.update(creation="ok", created_object=created.name)
        removed = trim_queue(spool, max_bytes=max_bytes, max_age_days=max_age)
        status["expired_pending_count"] = removed
        if removed:
            print(f"backup event=pending_expired count={removed}", flush=True)
        if upload_queue(spool, remote, status):
            try:
                run_command([
                    "rclone", "delete", remote, "--include", f"{PREFIX}*.dump.enc",
                    "--min-age", f"{retention}d", "--retries", "2", "--low-level-retries", "2",
                    "--contimeout", "15s", "--timeout", "60s",
                ], stdout=subprocess.DEVNULL)
                status["retention"] = "ok"
                exit_code = 0
            except (subprocess.SubprocessError, OSError) as exc:
                status["retention"] = "failed"
                status["retention_error"] = failure_reason(exc)
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        status["error_type"] = type(exc).__name__
        if status["creation"] == "pending":
            status["creation"] = "failed"
    finally:
        status["finished_at"] = time()
        status["pending_count"] = len(archives(spool))
        atomic_json(spool / "last-run.json", status)
        print("backup " + " ".join(f"{key}={status[key]}" for key in ("creation", "upload", "retention", "pending_count")), flush=True)
    return exit_code


def main() -> int:
    os.umask(0o077)
    spool = Path(os.environ.get("BACKUP_SPOOL_DIR", "/var/lib/financialassistant-backups"))
    spool.mkdir(parents=True, exist_ok=True, mode=0o700)
    if spool.is_symlink() or spool.stat().st_mode & 0o077:
        raise ValueError("Backup spool must be a private directory (0700)")
    with (spool / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("backup event=already_running")
            return 0
        return backup(spool)


if __name__ == "__main__":
    raise SystemExit(main())
