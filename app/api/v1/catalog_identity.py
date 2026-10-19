from app.schemas.catalog_package_replacement import PackageReplacementInput
from app.services.catalog_package_replacement_service import CatalogPackageReplacementService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.catalog_identity import VariantInput, OfferIdentityInput, ReceiptCodeLookupInput
from app.services.receipt_code_service import ReceiptCodeService
from app.services.catalog_identity_service import CatalogIdentityService

router = APIRouter(prefix='/operations/catalog-products', tags=['operations'])


def run(action):
    try:
        return action()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/lookup-codes')
def lookup_receipt_codes(payload: ReceiptCodeLookupInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: ReceiptCodeService(db).lookup(user_id=user_id, **payload.model_dump()))


@router.post('/lookup-site-codes')
def lookup_site_codes(payload: ReceiptCodeLookupInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    from app.services.receipt_site_service import ReceiptSiteService
    return run(lambda: ReceiptSiteService(db).lookup(user_id=user_id, **payload.model_dump()))


@router.get('/{product_id}/identity')
def get_identity(product_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogIdentityService(db).get(user_id=user_id, product_id=product_id))


@router.post('/{product_id}/variants', status_code=201)
def create_variant(product_id: int, payload: VariantInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogIdentityService(db).save_variant(user_id=user_id, product_id=product_id, data=payload.model_dump()))


@router.put('/{product_id}/variants/{variant_id}')
def update_variant(product_id: int, variant_id: int, payload: VariantInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogIdentityService(db).save_variant(user_id=user_id, product_id=product_id, variant_id=variant_id, data=payload.model_dump()))


@router.put('/{product_id}/offers/{template_id}/identity')
def save_offer_identity(product_id: int, template_id: int, payload: OfferIdentityInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogIdentityService(db).save_offer(user_id=user_id, product_id=product_id, template_id=template_id, data=payload.model_dump()))




@router.get('/{product_id}/package-replacements')
def get_replacements(product_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogPackageReplacementService(db).get(user_id=user_id, product_id=product_id))


@router.post('/{product_id}/package-replacements', status_code=201)
def confirm_replacement(product_id: int, payload: PackageReplacementInput, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogPackageReplacementService(db).create(user_id=user_id, product_id=product_id, data=payload.model_dump()))


@router.delete('/{product_id}/package-replacements/{replacement_id}')
def remove_replacement(product_id: int, replacement_id: int, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return run(lambda: CatalogPackageReplacementService(db).remove(user_id=user_id, product_id=product_id, replacement_id=replacement_id))
