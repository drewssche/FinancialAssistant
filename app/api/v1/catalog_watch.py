from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.catalog_watch_service import CatalogWatchService
from app.services.edostavka_provider import fetch_product, search_products
from app.services.catalog_identity_service import normalize_codes
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


class SearchCode(BaseModel):
    kind: Literal['barcode', 'retailer']
    code: str = Field(min_length=2, max_length=160)


class SearchInput(BaseModel):
    codes: list[SearchCode] = Field(default_factory=list, max_length=3)
    name: str | None = Field(default=None, min_length=2, max_length=160)


@router.post('/{product_id}/offers/{template_id}/search')
def search(product_id: int, template_id: int, payload: SearchInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    def action():
        service = CatalogWatchService(db)
        offer = service.offer(user_id, product_id, template_id)
        if not service.supports(offer):
            raise ValueError('Поиск доступен для источника Е-доставка или Евроопт.')
        if bool(payload.codes) == bool(payload.name):
            raise ValueError('Укажите коды или название для поиска.')
        queries = []
        for entry in payload.codes:
            code = entry.code.strip()
            if entry.kind == 'barcode':
                normalize_codes([code])
            if code not in [q for q, _ in queries]:
                queries.append((code, entry.kind))
        if payload.name:
            queries.append((payload.name.strip(), 'name'))
        results = {}
        for query, kind in queries:
            for hit in search_products(query):
                hit = dict(hit, matched_query=query, match_kind=kind)
                results.setdefault(hit['url'], hit)
        return {'items': list(results.values())[:8]}
    return run(action)
