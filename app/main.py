from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Operation  # noqa: F401
from app.services.categories import seed_default_categories


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("SKIP_DB_INIT") != "1":
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_default_categories(db)
        finally:
            db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)
