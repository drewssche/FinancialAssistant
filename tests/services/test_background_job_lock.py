from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.background_job_lock import (
    try_background_job_lock,
    try_background_transaction_job_lock,
)


def test_local_background_job_lock_rejects_overlapping_holder():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as first_db, Session(engine) as second_db:
        with try_background_job_lock(first_db, "currency-alerts") as first_acquired:
            assert first_acquired is True
            with try_background_job_lock(second_db, "currency-alerts") as second_acquired:
                assert second_acquired is False

        with try_background_job_lock(second_db, "currency-alerts") as acquired_after_release:
            assert acquired_after_release is True


def test_local_transaction_job_lock_rejects_overlapping_scheduler():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as first_db, Session(engine) as second_db:
        with try_background_transaction_job_lock(first_db, "currency-history") as first_acquired:
            assert first_acquired is True
            with try_background_transaction_job_lock(second_db, "currency-history") as second_acquired:
                assert second_acquired is False
            first_db.commit()

        with try_background_transaction_job_lock(second_db, "currency-history") as acquired_after_release:
            assert acquired_after_release is True


def test_postgres_background_lock_keeps_dedicated_connection_across_orm_commit():
    calls = []

    class _ScalarResult:
        def __init__(self, value):  # noqa: ANN001
            self.value = value

        def scalar(self):
            return self.value

    class _DedicatedConnection:
        def __init__(self):
            self.closed = False

        def __enter__(self):
            calls.append(("enter", self))
            return self

        def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
            self.closed = True
            calls.append(("close", self))

        def execute(self, statement, parameters):  # noqa: ANN001
            calls.append(("execute", self, str(statement), parameters))
            return _ScalarResult(True)

    class _Engine:
        dialect = type("Dialect", (), {"name": "postgresql"})()

        def __init__(self):
            self.connection = _DedicatedConnection()
            self.connect_count = 0

        def connect(self):
            self.connect_count += 1
            return self.connection

    class _Db:
        def __init__(self, engine):  # noqa: ANN001
            self.engine = engine
            self.commit_count = 0
            self.orm_connection_count = 0

        def get_bind(self):
            return self.engine

        def connection(self):
            self.orm_connection_count += 1
            raise AssertionError("advisory lock must not use the ORM Session connection")

        def commit(self):
            self.commit_count += 1

    engine = _Engine()
    db = _Db(engine)

    with try_background_job_lock(db, "manual-digest:7") as acquired:
        assert acquired is True
        db.commit()
        assert engine.connection.closed is False

    executions = [call for call in calls if call[0] == "execute"]
    assert engine.connect_count == 1
    assert db.commit_count == 1
    assert db.orm_connection_count == 0
    assert len(executions) == 2
    assert "pg_try_advisory_lock" in executions[0][2]
    assert "pg_advisory_unlock" in executions[1][2]
    assert executions[0][1] is executions[1][1] is engine.connection
    assert engine.connection.closed is True
