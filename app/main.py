from pathlib import Path
from time import perf_counter
from uuid import uuid4

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
from app.db.session import get_db

settings = get_settings()
settings.validate_runtime_requirements()
configure_logging()
base_dir = Path(__file__).resolve().parents[1]
static_dir = base_dir / "static"
index_file = static_dir / "index.html"
alembic_config = Config(str(base_dir / "alembic.ini"))
expected_database_revision = ScriptDirectory.from_config(alembic_config).get_current_head()

app = FastAPI(title=settings.app_name)
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
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    started_at = perf_counter()
    status_code = 500
    response = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        record_http_request(path=request.url.path, method=request.method)
        if response is not None:
            try:
                response_size = int(response.headers.get("Content-Length", "0"))
            except ValueError:
                response_size = 0
            record_http_response_size(path=request.url.path, method=request.method, size_bytes=response_size)
            response.headers["X-Request-ID"] = request_id
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-eval' https://telegram.org; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self' https://telegram.org https://oauth.telegram.org; "
                "frame-src https://oauth.telegram.org https://telegram.org; "
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
            path=request.url.path,
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
