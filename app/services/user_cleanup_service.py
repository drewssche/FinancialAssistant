from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuthIdentity,
    Category,
    CategoryGroup,
    Debt,
    DebtCounterparty,
    DebtIssuance,
    DebtRepayment,
    Operation,
    OperationItemPrice,
    OperationItemTemplate,
    OperationReceiptItem,
    User,
    UserPreference,
)


def hard_delete_user(db: Session, *, user_id: int) -> bool:
    debt_ids_subq = select(Debt.id).where(Debt.user_id == user_id)
    template_ids_subq = select(OperationItemTemplate.id).where(OperationItemTemplate.user_id == user_id)

    db.execute(delete(DebtRepayment).where(DebtRepayment.debt_id.in_(debt_ids_subq)))
    db.execute(delete(DebtIssuance).where(DebtIssuance.debt_id.in_(debt_ids_subq)))
    db.execute(delete(Debt).where(Debt.user_id == user_id))
    db.execute(delete(DebtCounterparty).where(DebtCounterparty.user_id == user_id))

    db.execute(delete(OperationReceiptItem).where(OperationReceiptItem.user_id == user_id))
    db.execute(delete(Operation).where(Operation.user_id == user_id))
    db.execute(delete(OperationItemPrice).where(OperationItemPrice.template_id.in_(template_ids_subq)))
    db.execute(delete(OperationItemTemplate).where(OperationItemTemplate.user_id == user_id))

    db.execute(delete(Category).where(Category.user_id == user_id))
    db.execute(delete(CategoryGroup).where(CategoryGroup.user_id == user_id))
    db.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
    db.execute(delete(AuthIdentity).where(AuthIdentity.user_id == user_id))
    user = db.get(User, user_id)
    if not user:
        db.commit()
        return False
    db.delete(user)
    db.commit()
    return True
