"""add persistent bank-rate history backfill jobs

Revision ID: 20260826_0040
Revises: 20260826_0039
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0040"
down_revision = "20260826_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_bank_rate_history_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("bank_codes", sa.JSON(), nullable=False),
        sa.Column("currencies", sa.JSON(), nullable=False),
        sa.Column("processed_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quotes_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_key"),
    )
    op.create_index(
        op.f("ix_fx_bank_rate_history_jobs_job_key"),
        "fx_bank_rate_history_jobs",
        ["job_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_fx_bank_rate_history_jobs_status"),
        "fx_bank_rate_history_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fx_bank_rate_history_jobs_updated_at"),
        "fx_bank_rate_history_jobs",
        ["updated_at"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(op.f("ix_fx_bank_rate_history_jobs_updated_at"), table_name="fx_bank_rate_history_jobs")
    op.drop_index(op.f("ix_fx_bank_rate_history_jobs_status"), table_name="fx_bank_rate_history_jobs")
    op.drop_index(op.f("ix_fx_bank_rate_history_jobs_job_key"), table_name="fx_bank_rate_history_jobs")
    op.drop_table("fx_bank_rate_history_jobs")
