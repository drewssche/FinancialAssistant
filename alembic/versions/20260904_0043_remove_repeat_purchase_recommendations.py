"""retire repeat purchase recommendations while preserving stored values

Revision ID: 20260904_0043
Revises: 20260904_0042
Create Date: 2026-09-04
"""

revision = "20260904_0043"
down_revision = "20260904_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The application no longer reads or writes these legacy fields. Keep the
    # stored values in place so retiring the feature is non-destructive; a
    # future cleanup migration may remove them after an explicit data-retention
    # decision.
    pass


def downgrade() -> None:
    pass
