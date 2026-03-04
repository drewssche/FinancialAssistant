from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.operation import OperationCreate, OperationOut
from app.services.operation_service import OperationService

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("", response_model=list[OperationOut])
def list_operations(
    period_days: int = Query(default=30, ge=1, le=365),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    return service.list_operations(user_id=user_id, period_days=period_days)


@router.post("", response_model=OperationOut)
def create_operation(
    payload: OperationCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = OperationService(db)
    return service.create_operation(
        user_id=user_id,
        kind=payload.kind,
        amount=payload.amount,
        operation_date=payload.operation_date,
        category_id=payload.category_id,
        note=payload.note,
    )
