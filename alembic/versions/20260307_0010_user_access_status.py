"""user access status pending/approved/rejected

Revision ID: 20260307_0010
Revises: 20260306_0009
Create Date: 2026-03-07 00:00:00
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260307_0010"
down_revision: Union[str, None] = "20260306_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET status = 'approved' WHERE status = 'active'")
    op.alter_column("users", "status", server_default=sa.text("'pending'"))
    op.create_index("ix_users_status", "users", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_status", table_name="users")
    op.execute("UPDATE users SET status = 'active' WHERE status = 'approved'")
    op.alter_column("users", "status", server_default=sa.text("'active'"))
