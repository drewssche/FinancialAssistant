from time import perf_counter

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.metrics import increment_counter, observe_latency_ms

settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    pool_recycle=settings.db_pool_recycle_seconds,
    pool_use_lifo=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


@event.listens_for(Engine, "before_cursor_execute")
def _start_query_timer(conn, cursor, statement, parameters, context, executemany):
    _ = cursor, statement, parameters, context, executemany
    conn.info.setdefault("query_started_at", []).append(perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def _record_query_metrics(conn, cursor, statement, parameters, context, executemany):
    _ = cursor, statement, parameters, context, executemany
    timers = conn.info.get("query_started_at", [])
    started_at = timers.pop() if timers else perf_counter()
    increment_counter("database_query_total")
    observe_latency_ms("database_query_latency_ms", (perf_counter() - started_at) * 1000.0)


@event.listens_for(Engine, "handle_error")
def _record_query_failure(exception_context):
    conn = exception_context.connection
    timers = conn.info.get("query_started_at", []) if conn is not None else []
    started_at = timers.pop() if timers else perf_counter()
    increment_counter("database_query_total")
    increment_counter("database_query_error_total")
    observe_latency_ms("database_query_latency_ms", (perf_counter() - started_at) * 1000.0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
