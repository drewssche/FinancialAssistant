from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.debt import DebtCardOut, DebtCreate, DebtOut, DebtRepaymentCreate, DebtRepaymentOut, DebtUpdate
from app.services.debt_service import DebtService

router = APIRouter(prefix="/debts", tags=["debts"])


@router.get("/cards", response_model=list[DebtCardOut])
def list_debt_cards(
    include_closed: bool = Query(default=False),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DebtService(db)
    try:
        return service.list_cards(user_id=user_id, include_closed=include_closed)
    except ProgrammingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Debt schema is not ready. Run database migrations (alembic upgrade head).",
        ) from exc


@router.post("", response_model=DebtOut, status_code=status.HTTP_201_CREATED)
def create_debt(
    payload: DebtCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DebtService(db)
    try:
        debt, _counterparty = service.create_debt(
            user_id=user_id,
            counterparty=payload.counterparty,
            direction=payload.direction,
            principal=payload.principal,
            start_date=payload.start_date,
            due_date=payload.due_date,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    item = service.get_debt_with_repayments(user_id=user_id, debt_id=debt.id)
    return DebtOut(**item)


@router.post("/{debt_id}/repayments", response_model=DebtRepaymentOut, status_code=status.HTTP_201_CREATED)
def create_repayment(
    debt_id: int,
    payload: DebtRepaymentCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DebtService(db)
    try:
        repayment = service.add_repayment(
            user_id=user_id,
            debt_id=debt_id,
            amount=payload.amount,
            repayment_date=payload.repayment_date,
            note=payload.note,
        )
        return repayment
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{debt_id}", response_model=DebtOut)
def update_debt(
    debt_id: int,
    payload: DebtUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DebtService(db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    try:
        debt = service.update_debt(user_id=user_id, debt_id=debt_id, updates=updates)
        item = service.get_debt_with_repayments(user_id=user_id, debt_id=debt.id)
        return DebtOut(**item)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_debt(
    debt_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = DebtService(db)
    try:
        service.delete_debt(user_id=user_id, debt_id=debt_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
