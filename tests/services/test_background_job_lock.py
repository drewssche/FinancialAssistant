from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.background_job_lock import try_background_job_lock


def test_local_background_job_lock_rejects_overlapping_holder():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as first_db, Session(engine) as second_db:
        with try_background_job_lock(first_db, "currency-alerts") as first_acquired:
            assert first_acquired is True
            with try_background_job_lock(second_db, "currency-alerts") as second_acquired:
                assert second_acquired is False

        with try_background_job_lock(second_db, "currency-alerts") as acquired_after_release:
            assert acquired_after_release is True
