from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, log_api_request_completion
from app.core.metrics import record_http_request

settings = get_settings()
settings.validate_runtime_requirements()
configure_logging()
base_dir = Path(__file__).resolve().parents[1]
static_dir = base_dir / "static"
index_file = static_dir / "index.html"

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
            response.headers["X-Request-ID"] = request_id
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


@app.get("/")
def home():
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "UI is not built yet"}
