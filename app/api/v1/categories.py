from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryOut
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    return service.list_categories(user_id)


@router.post("", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = CategoryService(db)
    return service.create_category(user_id=user_id, name=payload.name, kind=payload.kind)
