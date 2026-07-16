"""normalize NBRB rates to one currency unit

Revision ID: 20260716_0031
Revises: 20260627_0030
Create Date: 2026-07-16
"""

from alembic import op


revision = "20260716_0031"
down_revision = "20260627_0030"
branch_labels = None
depends_on = None


_LEGACY_SOURCES = "('nbrb_auto', 'nbrb_history')"
_UNIT_SOURCES = "('nbrb_auto_unit', 'nbrb_history_unit')"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE fx_rate_snapshots
        SET rate = CASE
                WHEN currency = 'RUB' THEN rate / 100
                WHEN currency IN ('CNY', 'PLN') THEN rate / 10
                ELSE rate
            END,
            source = CASE
                WHEN source = 'nbrb_history' THEN 'nbrb_history_unit'
                ELSE 'nbrb_auto_unit'
            END
        WHERE source IN {_LEGACY_SOURCES}
          AND currency IN ('USD', 'EUR', 'RUB', 'CNY', 'PLN')
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE fx_rate_snapshots
        SET rate = CASE
                WHEN currency = 'RUB' THEN rate * 100
                WHEN currency IN ('CNY', 'PLN') THEN rate * 10
                ELSE rate
            END,
            source = CASE
                WHEN source = 'nbrb_history_unit' THEN 'nbrb_history'
                ELSE 'nbrb_auto'
            END
        WHERE source IN {_UNIT_SOURCES}
          AND currency IN ('USD', 'EUR', 'RUB', 'CNY', 'PLN')
        """
    )
