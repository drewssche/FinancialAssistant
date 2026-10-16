from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.catalog_watch_service import CatalogWatchService
from app.services.edostavka_provider import fetch_product
from app.api.v1.catalog_identity import run

router = APIRouter(prefix='/catalog-watches', tags=['catalog'])


class WatchInput(BaseModel):
    enabled: bool


class LinkInput(BaseModel):
    url: str = Field(max_length=2048)
    expected_key: str = Field(max_length=2048)
    expected_name: str = Field(max_length=320)


class PreviewInput(BaseModel):
    url: str = Field(max_length=2048)


@router.get('')
def dashboard(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return CatalogWatchService(db).dashboard(user_id)


@router.get('/{product_id}')
def detail(product_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogWatchService(db).detail(user_id, product_id))


@router.put('/{product_id}')
def enabled(product_id: int, payload: WatchInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogWatchService(db).set_enabled(user_id, product_id, payload.enabled))


@router.post('/{product_id}/preview')
def preview(product_id: int, payload: PreviewInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    run(lambda: CatalogWatchService(db).product(user_id, product_id))
    return run(lambda: fetch_product(payload.url))


@router.put('/{product_id}/offers/{template_id}')
def connect(product_id: int, template_id: int, payload: LinkInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogWatchService(db).connect(user_id, product_id, template_id, **payload.model_dump()))


@router.delete('/{product_id}/offers/{template_id}')
def disconnect(product_id: int, template_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogWatchService(db).disconnect(user_id, product_id, template_id))
