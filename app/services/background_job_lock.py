from __future__ import annotations

from contextlib import contextmanager
from hashlib import blake2b
from threading import Lock
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session


_local_locks: dict[str, Lock] = {}
_local_locks_guard = Lock()


def _lock_id(name: str) -> int:
    raw = blake2b(name.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(raw, byteorder="big", signed=True)


def _get_local_lock(name: str) -> Lock:
    with _local_locks_guard:
        return _local_locks.setdefault(name, Lock())


@contextmanager
def try_background_job_lock(db: Session, name: str) -> Iterator[bool]:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        lock = _get_local_lock(name)
        acquired = lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()
        return

    connection = db.connection()
    lock_id = _lock_id(name)
    acquired = bool(
        connection.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": lock_id},
        ).scalar()
    )
    try:
        yield acquired
    finally:
        if acquired:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id},
            )
