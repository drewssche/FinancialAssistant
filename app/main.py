from pathlib import Path
from time import perf_counter
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, log_api_request_completion
from app.core.metrics import record_http_request, record_http_response_size
from app.core.security_observation import SecurityJournal, SecurityObserver, documentation_options, normalized_path
from app.db.session import get_db
from app.services.security_alert_service import SecurityAlerts

settings = get_settings()
settings.validate_runtime_requirements()
configure_logging()
base_dir = Path(__file__).resolve().parents[1]
static_dir = base_dir / "static"
index_file = static_dir / "index.html"
alembic_config = Config(str(base_dir / "alembic.ini"))
expected_database_revision = ScriptDirectory.from_config(alembic_config).get_current_head()

security_journal = SecurityJournal(settings.security_event_log_path) if settings.security_event_log_path else lambda event: None
security_alerts = SecurityAlerts(settings, security_journal) if settings.security_alerts_enabled and settings.security_event_log_path else None


def record_security_event(event):
    security_journal(event)
    if security_alerts:
        security_alerts.record(event)


@asynccontextmanager
async def lifespan(app):
    if security_alerts:
        security_alerts.start()
    yield
    if security_alerts:
        security_alerts.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan, **documentation_options(settings.is_production))
security_observer = SecurityObserver(
    record_security_event,
    trusted_proxy_ips=[ip.strip() for ip in settings.security_trusted_proxy_ips.split(",") if ip.strip()],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory=str(static_dir), check_dir=False), name="static")


@app.middleware("http")
async def http_metrics_middleware(request, call_next):
    # An untrusted request ID must not inject text into logs or response headers.
    request_id = str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()
    status_code = 500
    response = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        observed_path = normalized_path(request)
        security_observer.observe(request, status_code)
        record_http_request(path=observed_path, method=request.method)
        if response is not None:
            try:
                response_size = int(response.headers.get("Content-Length", "0"))
            except ValueError:
                response_size = 0
            record_http_response_size(path=observed_path, method=request.method, size_bytes=response_size)
            response.headers["X-Request-ID"] = request_id
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-eval' https://telegram.org; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' https://telegram.org https://oauth.telegram.org; "
                "frame-src 'self' https://oauth.telegram.org https://telegram.org; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'self' https://web.telegram.org"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "same-origin"
            path = request.url.path
            if path == "/" or path == "/static/index.html":
                response.headers["Cache-Control"] = "no-cache"
            elif path.startswith("/static/") and request.query_params.get("v"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif path.startswith("/static/"):
                response.headers["Cache-Control"] = "no-cache"
        log_api_request_completion(
            method=request.method,
            path=observed_path,
            status_code=status_code,
            duration_ms=(perf_counter() - started_at) * 1000.0,
            request_id=request_id,
        )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        current_revision = db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "unavailable"})
    if not current_revision or current_revision != expected_database_revision:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "migration_required",
                "current_revision": current_revision,
                "expected_revision": expected_database_revision,
            },
        )
    return {"status": "ready", "database": "ok", "revision": current_revision}


@app.get("/")
def home():
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "UI is not built yet"}
