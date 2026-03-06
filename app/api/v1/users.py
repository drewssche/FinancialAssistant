from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_id
from app.db.models import (
    AuthIdentity,
    Category,
    CategoryGroup,
    Debt,
    DebtCounterparty,
    DebtIssuance,
    DebtRepayment,
    Operation,
    User,
    UserPreference,
)
from app.db.session import get_db
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    debt_ids_subq = select(Debt.id).where(Debt.user_id == user_id)
    db.execute(delete(DebtRepayment).where(DebtRepayment.debt_id.in_(debt_ids_subq)))
    db.execute(delete(DebtIssuance).where(DebtIssuance.debt_id.in_(debt_ids_subq)))
    db.execute(delete(Debt).where(Debt.user_id == user_id))
    db.execute(delete(DebtCounterparty).where(DebtCounterparty.user_id == user_id))
    db.execute(delete(Operation).where(Operation.user_id == user_id))
    db.execute(delete(Category).where(Category.user_id == user_id))
    db.execute(delete(CategoryGroup).where(CategoryGroup.user_id == user_id))
    db.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
    db.execute(delete(AuthIdentity).where(AuthIdentity.user_id == user_id))
    user = db.get(User, user_id)
    if user:
        db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
