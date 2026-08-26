from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import FxBankRate, FxBankRateHistoryJob, FxBankRateSnapshot, User, UserPreference
from app.services.bank_currency_rate_history_backfill_service import (
    BankCurrencyRateHistoryBackfillService,
    _run_job_with_session,
)
from app.services.bank_currency_rate_refresh_service import BankCurrencyQuote, BankCurrencyRateRefreshService
from app.services.bank_currency_rate_registry import BANK_RATE_PROVIDERS


def _make_session(*, banks: list[str] | None = None):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    with SessionLocal() as db:
        db.add(User(id=1, display_name="Tester", status="active"))
        db.add(
            UserPreference(
                user_id=1,
                preferences_version=1,
                data={
                    "currency": {
                        "tracked_currencies": ["USD", "EUR", "RUB"],
                        "bank_rate_banks": banks
                        if banks is not None
                        else ["priorbank", "technobank", "bsb", "sber"],
                    },
                    "ui": {"currency": "BYN"},
                },
            )
        )
        db.commit()
    return engine, SessionLocal


def test_request_job_filters_to_configured_banks_and_exposes_capabilities():
    engine, SessionLocal = _make_session(banks=["priorbank", "technobank"])
    try:
        with SessionLocal() as db:
            payload, should_schedule = BankCurrencyRateHistoryBackfillService(db).request_job(
                user_id=1,
                bank_codes=["priorbank", "bsb", "technobank"],
                date_from=date(2026, 8, 25),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )

        assert should_schedule is True
        assert payload["status"] == "queued"
        assert payload["bank_codes"] == ["priorbank", "technobank"]
        assert payload["currencies"] == ["USD", "EUR", "RUB"]
        assert payload["total_steps"] == 2
        assert payload["progress"]["priorbank"]["capability"] == "backfill"
        assert payload["progress"]["technobank"]["status"] == "accumulating"
    finally:
        Base.metadata.drop_all(bind=engine)


def test_request_job_returns_same_active_job_without_resetting_progress():
    engine, SessionLocal = _make_session(banks=["priorbank"])
    try:
        with SessionLocal() as db:
            service = BankCurrencyRateHistoryBackfillService(db)
            first, first_schedule = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 25),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            second, second_schedule = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 1),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )

        assert first_schedule is True
        assert second_schedule is False
        assert second["id"] == first["id"]
        assert second["date_from"] == date(2026, 8, 25)
        assert second["total_steps"] == 2
    finally:
        Base.metadata.drop_all(bind=engine)


def test_stale_running_job_is_reported_interrupted_and_resumes_checkpoint():
    engine, SessionLocal = _make_session(banks=["priorbank"])
    try:
        with SessionLocal() as db:
            service = BankCurrencyRateHistoryBackfillService(db)
            original, _ = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 24),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            job = db.get(FxBankRateHistoryJob, original["id"])
            progress = dict(job.progress)
            prior = dict(progress["priorbank"])
            prior.update(
                {
                    "status": "running",
                    "processed_days": 1,
                    "last_processed_date": "2026-08-24",
                    "quotes_processed": 2,
                }
            )
            progress["priorbank"] = prior
            job.status = "running"
            job.progress = progress
            job.processed_steps = 1
            job.quotes_processed = 2
            job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=11)
            db.commit()

            interrupted = service.get_status()
            resumed, should_schedule = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 24),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )

        assert interrupted["status"] == "interrupted"
        assert interrupted["resumable"] is True
        assert should_schedule is True
        assert resumed["id"] == original["id"]
        assert resumed["status"] == "queued"
        assert resumed["processed_steps"] == 1
        assert resumed["progress"]["priorbank"]["last_processed_date"] == "2026-08-24"
    finally:
        Base.metadata.drop_all(bind=engine)


def test_job_runner_backfills_snapshots_without_touching_current_rates(monkeypatch):
    engine, SessionLocal = _make_session(banks=["priorbank", "bsb"])

    def _fake_history(self, *, client, bank_code, target_date, currencies):
        _ = client, currencies
        provider = BANK_RATE_PROVIDERS[bank_code]
        return [
            BankCurrencyQuote(
                bank_code=bank_code,
                bank_name=str(provider["name"]),
                currency="EUR",
                scale=1,
                buy_rate=Decimal("3.420000"),
                sell_rate=Decimal("3.520000"),
                channel=str(provider["channel"]),
                location_name=None,
                source_url="https://example.test/archive",
                quoted_at=datetime(
                    target_date.year,
                    target_date.month,
                    target_date.day,
                    17,
                    tzinfo=timezone.utc,
                ),
            )
        ], []

    monkeypatch.setattr(
        BankCurrencyRateRefreshService,
        "fetch_historical_quotes_for_day",
        _fake_history,
    )
    try:
        with SessionLocal() as db:
            payload, _ = BankCurrencyRateHistoryBackfillService(db).request_job(
                user_id=1,
                bank_codes=["priorbank", "bsb"],
                date_from=date(2026, 8, 25),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            _run_job_with_session(db, job_id=payload["id"])

            job = db.get(FxBankRateHistoryJob, payload["id"])
            history_count = db.scalar(select(func.count()).select_from(FxBankRateSnapshot))
            current_count = db.scalar(select(func.count()).select_from(FxBankRate))

            repeated, repeated_schedule = BankCurrencyRateHistoryBackfillService(db).request_job(
                user_id=1,
                bank_codes=["priorbank", "bsb"],
                date_from=date(2026, 8, 25),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            _run_job_with_session(db, job_id=repeated["id"])
            repeated_history_count = db.scalar(select(func.count()).select_from(FxBankRateSnapshot))
            repeated_job = db.get(FxBankRateHistoryJob, repeated["id"])

        assert job.status == "completed"
        assert job.processed_steps == 4
        assert job.total_steps == 4
        assert job.quotes_processed == 4
        assert history_count == 4
        assert current_count == 0
        assert repeated_schedule is True
        assert repeated_history_count == 4
        assert repeated_job.status == "completed"
        assert repeated_job.quotes_processed == 4
    finally:
        Base.metadata.drop_all(bind=engine)


def test_resumed_runner_starts_after_persisted_checkpoint(monkeypatch):
    engine, SessionLocal = _make_session(banks=["priorbank"])
    requested_dates = []

    def _fake_history(self, *, client, bank_code, target_date, currencies):
        _ = self, client, bank_code, currencies
        requested_dates.append(target_date)
        return [], []

    monkeypatch.setattr(
        BankCurrencyRateRefreshService,
        "fetch_historical_quotes_for_day",
        _fake_history,
    )
    try:
        with SessionLocal() as db:
            service = BankCurrencyRateHistoryBackfillService(db)
            original, _ = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 24),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            job = db.get(FxBankRateHistoryJob, original["id"])
            progress = dict(job.progress)
            prior = dict(progress["priorbank"])
            prior.update(
                {
                    "status": "running",
                    "processed_days": 1,
                    "last_processed_date": "2026-08-24",
                }
            )
            progress["priorbank"] = prior
            job.status = "running"
            job.progress = progress
            job.processed_steps = 1
            job.updated_at = datetime.now(timezone.utc) - timedelta(minutes=11)
            db.commit()

            resumed, should_schedule = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 24),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            _run_job_with_session(db, job_id=resumed["id"])
            completed = db.get(FxBankRateHistoryJob, resumed["id"])

        assert should_schedule is True
        assert requested_dates == [date(2026, 8, 25), date(2026, 8, 26)]
        assert completed.status == "completed"
        assert completed.processed_steps == 3
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.mark.parametrize(
    ("terminal_status", "persisted_quotes"),
    [("partial", 1), ("failed", 0)],
)
def test_terminal_retry_restarts_incomplete_provider_from_range_start(
    monkeypatch,
    terminal_status,
    persisted_quotes,
):
    engine, SessionLocal = _make_session(banks=["priorbank"])
    requested_dates = []

    def _fake_history(self, *, client, bank_code, target_date, currencies):
        _ = self, client, currencies
        requested_dates.append(target_date)
        provider = BANK_RATE_PROVIDERS[bank_code]
        return [
            BankCurrencyQuote(
                bank_code=bank_code,
                bank_name=str(provider["name"]),
                currency="EUR",
                scale=1,
                buy_rate=Decimal("3.420000"),
                sell_rate=Decimal("3.520000"),
                channel=str(provider["channel"]),
                location_name=None,
                source_url="https://example.test/archive",
                quoted_at=datetime(
                    target_date.year,
                    target_date.month,
                    target_date.day,
                    17,
                    tzinfo=timezone.utc,
                ),
            )
        ], []

    monkeypatch.setattr(
        BankCurrencyRateRefreshService,
        "fetch_historical_quotes_for_day",
        _fake_history,
    )
    try:
        with SessionLocal() as db:
            service = BankCurrencyRateHistoryBackfillService(db)
            original, _ = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 24),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            job = db.get(FxBankRateHistoryJob, original["id"])
            progress = dict(job.progress)
            prior = dict(progress["priorbank"])
            prior.update(
                {
                    "status": terminal_status,
                    "processed_days": 1,
                    "last_processed_date": "2026-08-24",
                    "quotes_processed": persisted_quotes,
                    "error_count": 1,
                    "message": "Временная ошибка официального архива",
                }
            )
            progress["priorbank"] = prior
            job.status = terminal_status
            job.progress = progress
            job.processed_steps = 1
            job.quotes_processed = persisted_quotes
            job.error_count = 1
            job.last_error = prior["message"]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()

            resumed, should_schedule = service.request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 24),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            _run_job_with_session(db, job_id=resumed["id"])
            finished = db.get(FxBankRateHistoryJob, resumed["id"])

        assert should_schedule is True
        assert resumed["id"] == original["id"]
        assert resumed["status"] == "queued"
        assert resumed["processed_steps"] == 0
        assert resumed["quotes_processed"] == 0
        assert resumed["error_count"] == 0
        assert resumed["progress"]["priorbank"]["last_processed_date"] is None
        assert requested_dates == [date(2026, 8, 24), date(2026, 8, 25), date(2026, 8, 26)]
        assert finished.status == "completed"
        assert finished.processed_steps == 3
        assert finished.quotes_processed == 3
        assert finished.error_count == 0
        assert finished.progress["priorbank"]["last_processed_date"] == "2026-08-26"
    finally:
        Base.metadata.drop_all(bind=engine)


def test_week_long_empty_official_archive_is_reported_as_failed(monkeypatch):
    engine, SessionLocal = _make_session(banks=["priorbank"])

    def _empty_history(self, *, client, bank_code, target_date, currencies):
        _ = self, client, bank_code, target_date, currencies
        return [], []

    monkeypatch.setattr(
        BankCurrencyRateRefreshService,
        "fetch_historical_quotes_for_day",
        _empty_history,
    )
    try:
        with SessionLocal() as db:
            payload, _ = BankCurrencyRateHistoryBackfillService(db).request_job(
                user_id=1,
                bank_codes=["priorbank"],
                date_from=date(2026, 8, 20),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )
            _run_job_with_session(db, job_id=payload["id"])
            failed = db.get(FxBankRateHistoryJob, payload["id"])

        provider = failed.progress["priorbank"]
        assert failed.status == "failed"
        assert failed.processed_steps == 7
        assert failed.quotes_processed == 0
        assert failed.error_count == 1
        assert provider["status"] == "failed"
        assert provider["error_count"] == 1
        assert "не вернул ни одной котировки" in provider["message"]
        assert failed.last_error == provider["message"]
    finally:
        Base.metadata.drop_all(bind=engine)


def test_non_archive_bank_completes_without_background_task():
    engine, SessionLocal = _make_session(banks=["technobank"])
    try:
        with SessionLocal() as db:
            payload, should_schedule = BankCurrencyRateHistoryBackfillService(db).request_job(
                user_id=1,
                bank_codes=["technobank"],
                date_from=date(2026, 8, 25),
                date_to=date(2026, 8, 26),
                today=date(2026, 8, 26),
            )

        assert should_schedule is False
        assert payload["status"] == "completed"
        assert payload["total_steps"] == 0
        assert payload["progress"]["technobank"]["capability"] == "accumulating"
    finally:
        Base.metadata.drop_all(bind=engine)
