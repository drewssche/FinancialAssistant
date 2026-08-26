from __future__ import annotations

from contextlib import contextmanager
from hashlib import blake2b
from threading import Lock
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Connection
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

    # PostgreSQL advisory locks are connection-scoped rather than
    # transaction-scoped. Keep a dedicated connection until the matching
    # unlock, even if work inside the context commits its ORM Session.
    engine = bind.engine if isinstance(bind, Connection) else bind
    lock_id = _lock_id(name)
    with engine.connect() as connection:
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


@contextmanager
def try_background_transaction_job_lock(db: Session, name: str) -> Iterator[bool]:
    """Try a lock that remains held until the current transaction finishes.

    This variant is intended for short scheduling transactions that must commit
    their durable checkpoint while still excluding concurrent schedulers.  The
    session-level helper above remains the right choice for a long-running job
    when the lock is kept in a dedicated, non-committing session.
    """

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

    acquired = bool(
        db.connection()
        .execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": _lock_id(name)},
        )
        .scalar()
    )
    yield acquired
