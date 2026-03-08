from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
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
    response = await call_next(request)
    record_http_request(path=request.url.path, method=request.method)
    return response


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def home():
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "UI is not built yet"}
