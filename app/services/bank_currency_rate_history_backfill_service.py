from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import log_background_job_event
from app.db.models import FxBankRateHistoryJob
from app.db.session import SessionLocal
from app.repositories.currency_repo import CurrencyRepository
from app.services.background_job_lock import (
    try_background_job_lock,
    try_background_transaction_job_lock,
)
from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService, MINSK_TZ
from app.services.bank_currency_rate_registry import BANK_RATE_PROVIDERS
from app.services.currency_service import CurrencyService


JOB_KEY = "global-bank-rate-history"
SCHEDULE_LOCK = "bank-currency-rate-history-backfill-schedule"
RUN_LOCK = "bank-currency-rate-history-backfill-run"
BACKFILL_BANK_CODES = ("priorbank", "bsb")
ACTIVE_STATUSES = {"queued", "running"}
DEFAULT_BACKFILL_DAYS = 90
MAX_BACKFILL_DAYS = 366
EMPTY_ARCHIVE_FAILURE_MIN_DAYS = 7
STALE_AFTER = timedelta(minutes=10)


class BankCurrencyRateHistoryBackfillService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CurrencyRepository(db)
        self.currency_service = CurrencyService(db)

    def request_job(
        self,
        *,
        user_id: int,
        bank_codes: list[str] | None,
        date_from: date | None,
        date_to: date | None,
        today: date | None = None,
    ) -> tuple[dict[str, Any], bool]:
        # The application is Belarus-specific and bank archives use local
        # calendar days, so normalize the upper bound using the same timezone
        # as provider timestamps.
        today = today or datetime.now(MINSK_TZ).date()
        normalized_from, normalized_to = self._normalize_range(
            date_from=date_from,
            date_to=date_to,
            today=today,
        )
        selected_codes, currencies = self._resolve_scope(
            user_id=user_id,
            bank_codes=bank_codes,
        )
        now = datetime.now(timezone.utc)

        with try_background_transaction_job_lock(self.db, SCHEDULE_LOCK) as acquired:
            if not acquired:
                self.db.rollback()
                raise RuntimeError("Bank rate history scheduling is busy; retry shortly")

            job = self.repo.get_bank_rate_history_job(job_key=JOB_KEY, for_update=True)
            if job is not None and job.status in ACTIVE_STATUSES and not self._is_stale(job, now=now):
                payload = self.serialize(job, now=now)
                self.db.rollback()
                return payload, False

            same_scope = bool(
                job is not None
                and job.date_from == normalized_from
                and job.date_to == normalized_to
                and list(job.bank_codes or []) == selected_codes
                and list(job.currencies or []) == currencies
            )
            terminal_retry = bool(job is not None and job.status in {"partial", "failed"})
            resumable = bool(
                job is not None
                and job.status in ACTIVE_STATUSES | {"partial", "failed"}
                and same_scope
            )
            if resumable:
                progress = self._resume_progress(
                    dict(job.progress or {}),
                    reset_incomplete=terminal_retry,
                )
                job.status = "queued"
                job.requested_at = now
                job.started_at = None
                job.finished_at = None
                job.last_error = None
                job.progress = progress
                _refresh_job_totals(job)
                job.updated_at = now
            else:
                progress = self._initial_progress(
                    bank_codes=selected_codes,
                    date_from=normalized_from,
                    date_to=normalized_to,
                )
                total_steps = self._total_steps(progress)
                if job is None:
                    job = self.repo.add_bank_rate_history_job(
                        FxBankRateHistoryJob(
                            job_key=JOB_KEY,
                            status="queued" if total_steps else "completed",
                            date_from=normalized_from,
                            date_to=normalized_to,
                            bank_codes=selected_codes,
                            currencies=currencies,
                            processed_steps=0,
                            total_steps=total_steps,
                            quotes_processed=0,
                            error_count=0,
                            progress=progress,
                            last_error=None,
                            requested_at=now,
                            started_at=None,
                            finished_at=None if total_steps else now,
                            updated_at=now,
                        )
                    )
                else:
                    job.status = "queued" if total_steps else "completed"
                    job.date_from = normalized_from
                    job.date_to = normalized_to
                    job.bank_codes = selected_codes
                    job.currencies = currencies
                    job.processed_steps = 0
                    job.total_steps = total_steps
                    job.quotes_processed = 0
                    job.error_count = 0
                    job.progress = progress
                    job.last_error = None
                    job.requested_at = now
                    job.started_at = None
                    job.finished_at = None if total_steps else now
                    job.updated_at = now

            self.db.commit()
            self.db.refresh(job)
            should_schedule = job.status == "queued"
            payload = self.serialize(job, now=now)

        log_background_job_event(
            "bank_currency_rate_history_backfill",
            "job_queued" if should_schedule else "no_archive_provider_selected",
            job_id=job.id,
            date_from=job.date_from,
            date_to=job.date_to,
            banks=list(job.bank_codes or []),
            currencies=list(job.currencies or []),
            resumed=resumable,
        )
        return payload, should_schedule

    def get_status(self) -> dict[str, Any] | None:
        job = self.repo.get_bank_rate_history_job(job_key=JOB_KEY)
        return self.serialize(job) if job is not None else None

    def _resolve_scope(
        self,
        *,
        user_id: int,
        bank_codes: list[str] | None,
    ) -> tuple[list[str], list[str]]:
        preferences = self.currency_service.get_currency_preferences(user_id)
        configured_codes = list(preferences.get("bank_rate_banks") or [])
        if bank_codes is None:
            selected_codes = configured_codes
        else:
            requested_codes = []
            for raw_code in bank_codes:
                code = str(raw_code or "").strip().lower()
                if not code:
                    continue
                if code not in BANK_RATE_PROVIDERS:
                    raise ValueError(f"Unsupported bank code: {code}")
                if code not in requested_codes:
                    requested_codes.append(code)
            selected_codes = [code for code in requested_codes if code in configured_codes]
        if not selected_codes:
            raise ValueError("None of the requested banks are enabled in currency settings")

        supported_currencies = set(BankCurrencyRateRefreshService.ISO_CODE_TO_NUMERIC)
        currencies = [
            code
            for code in preferences.get("tracked_currencies") or []
            if code != "BYN" and code in supported_currencies
        ]
        if not currencies:
            raise ValueError("No supported tracked currencies are configured")
        return selected_codes, list(dict.fromkeys(currencies))

    @staticmethod
    def _normalize_range(
        *,
        date_from: date | None,
        date_to: date | None,
        today: date,
    ) -> tuple[date, date]:
        normalized_to = date_to or today
        normalized_from = date_from or (normalized_to - timedelta(days=DEFAULT_BACKFILL_DAYS - 1))
        if normalized_from > normalized_to:
            raise ValueError("date_from must be on or before date_to")
        if normalized_to > today:
            raise ValueError("date_to cannot be in the future")
        days = (normalized_to - normalized_from).days + 1
        if days > MAX_BACKFILL_DAYS:
            raise ValueError(f"Bank rate history range cannot exceed {MAX_BACKFILL_DAYS} days")
        return normalized_from, normalized_to

    @staticmethod
    def _initial_progress(
        *,
        bank_codes: list[str],
        date_from: date,
        date_to: date,
    ) -> dict[str, dict[str, Any]]:
        total_days = (date_to - date_from).days + 1
        progress: dict[str, dict[str, Any]] = {}
        for code in bank_codes:
            bank_name = str(BANK_RATE_PROVIDERS[code]["name"])
            if code in BACKFILL_BANK_CODES:
                progress[code] = {
                    "bank_name": bank_name,
                    "capability": "backfill",
                    "status": "queued",
                    "processed_days": 0,
                    "total_days": total_days,
                    "quotes_processed": 0,
                    "error_count": 0,
                    "last_processed_date": None,
                    "message": None,
                }
            elif code == "technobank":
                progress[code] = {
                    "bank_name": bank_name,
                    "capability": "accumulating",
                    "status": "accumulating",
                    "processed_days": 0,
                    "total_days": 0,
                    "quotes_processed": 0,
                    "error_count": 0,
                    "last_processed_date": None,
                    "message": "Официальный архив недоступен; история накапливается с ежедневных котировок",
                }
            else:
                progress[code] = {
                    "bank_name": bank_name,
                    "capability": "unavailable",
                    "status": "unavailable",
                    "processed_days": 0,
                    "total_days": 0,
                    "quotes_processed": 0,
                    "error_count": 0,
                    "last_processed_date": None,
                    "message": "Доступный официальный архив не найден",
                }
        return progress

    @staticmethod
    def _resume_progress(
        progress: dict[str, Any],
        *,
        reset_incomplete: bool = False,
    ) -> dict[str, Any]:
        resumed: dict[str, Any] = {}
        for code, raw in progress.items():
            item = dict(raw) if isinstance(raw, dict) else {}
            if item.get("capability") == "backfill" and item.get("status") != "completed":
                item["status"] = "queued"
            if (
                reset_incomplete
                and item.get("capability") == "backfill"
                and item.get("status") != "completed"
            ):
                # A terminal checkpoint may already be past dates that failed
                # to fetch or parse. Re-run only the incomplete provider from
                # the range start. Snapshot upserts are idempotent, while
                # completed providers stay untouched.
                item.update(
                    {
                        "status": "queued",
                        "processed_days": 0,
                        "quotes_processed": 0,
                        "error_count": 0,
                        "last_processed_date": None,
                        "message": None,
                    }
                )
            resumed[code] = item
        return resumed

    @staticmethod
    def _total_steps(progress: dict[str, Any]) -> int:
        return sum(
            int(item.get("total_days") or 0)
            for item in progress.values()
            if isinstance(item, dict) and item.get("capability") == "backfill"
        )

    @classmethod
    def _is_stale(cls, job: FxBankRateHistoryJob, *, now: datetime | None = None) -> bool:
        if job.status not in ACTIVE_STATUSES:
            return False
        now = now or datetime.now(timezone.utc)
        updated_at = cls._aware(job.updated_at)
        return updated_at < now - STALE_AFTER

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @classmethod
    def serialize(
        cls,
        job: FxBankRateHistoryJob,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        interrupted = cls._is_stale(job, now=now)
        return {
            "id": int(job.id),
            "status": "interrupted" if interrupted else job.status,
            "resumable": interrupted or job.status in {"partial", "failed"},
            "date_from": job.date_from,
            "date_to": job.date_to,
            "bank_codes": list(job.bank_codes or []),
            "currencies": list(job.currencies or []),
            "processed_steps": int(job.processed_steps or 0),
            "total_steps": int(job.total_steps or 0),
            "quotes_processed": int(job.quotes_processed or 0),
            "error_count": int(job.error_count or 0),
            "progress": dict(job.progress or {}),
            "last_error": job.last_error,
            "requested_at": job.requested_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "updated_at": job.updated_at,
        }


def run_bank_rate_history_backfill_job(job_id: int, bind: Engine | None = None) -> None:
    session_factory = (
        SessionLocal
        if bind is None
        else sessionmaker(bind=bind, autocommit=False, autoflush=False, class_=Session)
    )
    lock_db = session_factory()
    try:
        with try_background_job_lock(lock_db, RUN_LOCK) as acquired:
            if not acquired:
                return
            work_db = session_factory()
            try:
                _run_job_with_session(work_db, job_id=job_id)
            finally:
                work_db.close()
    finally:
        lock_db.close()


def _run_job_with_session(db: Session, *, job_id: int) -> None:
    job = db.get(FxBankRateHistoryJob, job_id)
    if job is None:
        return
    now = datetime.now(timezone.utc)
    if job.status == "running" and not BankCurrencyRateHistoryBackfillService._is_stale(job, now=now):
        return
    if job.status not in ACTIVE_STATUSES:
        return

    progress = dict(job.progress or {})
    for code, raw in progress.items():
        item = dict(raw) if isinstance(raw, dict) else {}
        if item.get("capability") == "backfill" and item.get("status") != "completed":
            item["status"] = "running"
        progress[code] = item
    job.status = "running"
    job.started_at = job.started_at or now
    job.finished_at = None
    job.progress = progress
    job.updated_at = now
    db.commit()

    history_service = BankCurrencyRateRefreshService(db)
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru",
        "User-Agent": "FinancialAssistant/1.0 (+bank rate history backfill)",
    }
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
            for bank_code in job.bank_codes or []:
                if bank_code not in BACKFILL_BANK_CODES:
                    continue
                job = db.get(FxBankRateHistoryJob, job_id)
                if job is None:
                    return
                progress = dict(job.progress or {})
                provider = dict(progress.get(bank_code) or {})
                start_date = job.date_from
                checkpoint = provider.get("last_processed_date")
                if checkpoint:
                    try:
                        start_date = max(start_date, date.fromisoformat(str(checkpoint)) + timedelta(days=1))
                    except ValueError:
                        pass
                target_date = start_date
                while target_date <= job.date_to:
                    quotes, errors = history_service.fetch_historical_quotes_for_day(
                        client=client,
                        bank_code=bank_code,
                        target_date=target_date,
                        currencies=list(job.currencies or []),
                    )
                    fetched_at = datetime.now(timezone.utc)
                    saved = 0
                    for quote in quotes:
                        rate_date = history_service._quote_date(quote=quote, fetched_at=fetched_at)
                        if rate_date < job.date_from or rate_date > job.date_to:
                            continue
                        history_service.repo.upsert_bank_rate_snapshot(
                            bank_code=quote.bank_code,
                            bank_name=quote.bank_name,
                            currency=quote.currency,
                            base_currency="BYN",
                            rate_date=rate_date,
                            scale=quote.scale,
                            buy_rate=quote.buy_rate,
                            sell_rate=quote.sell_rate,
                            channel=quote.channel,
                            location_name=quote.location_name,
                            source_url=quote.source_url,
                            quoted_at=quote.quoted_at,
                            fetched_at=fetched_at,
                        )
                        saved += 1

                    job = db.get(FxBankRateHistoryJob, job_id)
                    progress = dict(job.progress or {})
                    provider = dict(progress.get(bank_code) or {})
                    provider["status"] = "running"
                    provider["processed_days"] = int(provider.get("processed_days") or 0) + 1
                    provider["quotes_processed"] = int(provider.get("quotes_processed") or 0) + saved
                    provider["error_count"] = int(provider.get("error_count") or 0) + len(errors)
                    provider["last_processed_date"] = target_date.isoformat()
                    if errors:
                        provider["message"] = "; ".join(errors)[-500:]
                    progress[bank_code] = provider
                    job.progress = progress
                    _refresh_job_totals(job)
                    job.last_error = provider["message"] if errors else job.last_error
                    job.updated_at = fetched_at
                    db.commit()
                    target_date += timedelta(days=1)

                job = db.get(FxBankRateHistoryJob, job_id)
                progress = dict(job.progress or {})
                provider = dict(progress.get(bank_code) or {})
                provider_errors = int(provider.get("error_count") or 0)
                provider_saved = int(provider.get("quotes_processed") or 0)
                provider_days = int(provider.get("processed_days") or 0)
                provider_total_days = int(provider.get("total_days") or 0)
                if (
                    provider_total_days >= EMPTY_ARCHIVE_FAILURE_MIN_DAYS
                    and provider_days >= provider_total_days
                    and provider_saved == 0
                    and provider_errors == 0
                ):
                    bank_name = str(provider.get("bank_name") or bank_code)
                    message = (
                        f"Официальный архив «{bank_name}» не вернул ни одной котировки "
                        f"за {provider_total_days} дн.; проверьте доступность источника "
                        "и повторите загрузку"
                    )
                    provider_errors = 1
                    provider["error_count"] = provider_errors
                    provider["message"] = message
                provider["status"] = (
                    "completed"
                    if provider_errors == 0
                    else ("partial" if provider_saved > 0 else "failed")
                )
                progress[bank_code] = provider
                job.progress = progress
                if provider_errors and provider.get("message"):
                    job.last_error = str(provider["message"])[-500:]
                job.updated_at = datetime.now(timezone.utc)
                db.commit()

        job = db.get(FxBankRateHistoryJob, job_id)
        _refresh_job_totals(job)
        job.status = (
            "completed"
            if job.error_count == 0
            else ("partial" if job.quotes_processed > 0 else "failed")
        )
        job.finished_at = datetime.now(timezone.utc)
        job.updated_at = job.finished_at
        db.commit()
        log_background_job_event(
            "bank_currency_rate_history_backfill",
            "job_finished",
            job_id=job.id,
            status=job.status,
            processed_steps=job.processed_steps,
            total_steps=job.total_steps,
            quotes_processed=job.quotes_processed,
            error_count=job.error_count,
        )
    except Exception as exc:  # noqa: BLE001 - persist a recoverable terminal state
        db.rollback()
        job = db.get(FxBankRateHistoryJob, job_id)
        if job is not None:
            job.status = "failed"
            job.last_error = f"{type(exc).__name__}: {exc}"[-500:]
            job.finished_at = datetime.now(timezone.utc)
            job.updated_at = job.finished_at
            db.commit()
        log_background_job_event(
            "bank_currency_rate_history_backfill",
            "job_failed",
            job_id=job_id,
            error=type(exc).__name__,
        )


def _refresh_job_totals(job: FxBankRateHistoryJob) -> None:
    provider_rows = [
        item
        for item in (job.progress or {}).values()
        if isinstance(item, dict) and item.get("capability") == "backfill"
    ]
    job.processed_steps = sum(int(item.get("processed_days") or 0) for item in provider_rows)
    job.total_steps = sum(int(item.get("total_days") or 0) for item in provider_rows)
    job.quotes_processed = sum(int(item.get("quotes_processed") or 0) for item in provider_rows)
    job.error_count = sum(int(item.get("error_count") or 0) for item in provider_rows)
