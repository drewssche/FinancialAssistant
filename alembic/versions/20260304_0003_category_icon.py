"""category icon field

Revision ID: 20260304_0003
Revises: 20260304_0002
Create Date: 2026-03-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260304_0003"
down_revision: Union[str, None] = "20260304_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("icon", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "icon")

