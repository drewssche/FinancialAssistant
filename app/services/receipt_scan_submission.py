from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models.receipt_scan_submission import ReceiptScanSubmission


class ReceiptSubmissionConflict(ValueError):
    pass


def reserve_submission(db: Session, user_id: int, key: str, payload_hash: str) -> ReceiptScanSubmission:
    # A concurrent insert waits for the first transaction to commit or roll back.
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    statement = insert(ReceiptScanSubmission).values(user_id=user_id, request_key=key, payload_hash=payload_hash)
    created = db.scalar(statement.on_conflict_do_nothing(
        index_elements=["user_id", "request_key"],
    ).returning(ReceiptScanSubmission))
    if created is not None:
        return created
    submission = db.get(ReceiptScanSubmission, (user_id, key))
    if submission.payload_hash != payload_hash:
        raise ReceiptSubmissionConflict("Этот чек уже отправлен с другими данными.")
    if submission.operation_id is None:
        raise ReceiptSubmissionConflict("Расход по этому чеку был записан и затем удалён.")
    return submission
