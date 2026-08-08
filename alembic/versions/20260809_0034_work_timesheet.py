"""add work timesheet and payroll plan links

Revision ID: 20260809_0034
Revises: 20260808_0033
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260809_0034"
down_revision = "20260808_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=True),
        sa.Column("position", sa.String(length=160), nullable=True),
        sa.Column("employment_start_date", sa.Date(), nullable=True),
        sa.Column("standard_hours_per_day", sa.Numeric(precision=5, scale=2), nullable=False, server_default="8.00"),
        sa.Column("workweek_mask", sa.String(length=32), nullable=False, server_default="0,1,2,3,4"),
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="BY"),
        sa.Column("advance_plan_id", sa.Integer(), nullable=True),
        sa.Column("salary_plan_id", sa.Integer(), nullable=True),
        sa.Column("advance_nominal_day", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("salary_nominal_day", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("payment_shift_rule", sa.String(length=32), nullable=False, server_default="previous_workday"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["advance_plan_id"], ["plan_operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["salary_plan_id"], ["plan_operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("advance_plan_id"),
        sa.UniqueConstraint("salary_plan_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_work_profiles_user_id"), "work_profiles", ["user_id"], unique=True)
    op.create_table(
        "employment_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("work_profile_id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("company", sa.String(length=160), nullable=True),
        sa.Column("position", sa.String(length=160), nullable=True),
        sa.Column("salary_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BYN"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_profile_id"], ["work_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employment_contracts_effective_from"), "employment_contracts", ["effective_from"], unique=False)
    op.create_index(op.f("ix_employment_contracts_user_id"), "employment_contracts", ["user_id"], unique=False)
    op.create_index(op.f("ix_employment_contracts_work_profile_id"), "employment_contracts", ["work_profile_id"], unique=False)
    op.create_table(
        "work_day_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("work_profile_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planned_hours", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("actual_hours", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("credited_hours", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_profile_id"], ["work_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "work_date", name="uq_work_day_overrides_user_date"),
    )
    op.create_index(op.f("ix_work_day_overrides_status"), "work_day_overrides", ["status"], unique=False)
    op.create_index(op.f("ix_work_day_overrides_user_id"), "work_day_overrides", ["user_id"], unique=False)
    op.create_index(op.f("ix_work_day_overrides_work_date"), "work_day_overrides", ["work_date"], unique=False)
    op.create_index(op.f("ix_work_day_overrides_work_profile_id"), "work_day_overrides", ["work_profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_work_day_overrides_work_profile_id"), table_name="work_day_overrides")
    op.drop_index(op.f("ix_work_day_overrides_work_date"), table_name="work_day_overrides")
    op.drop_index(op.f("ix_work_day_overrides_user_id"), table_name="work_day_overrides")
    op.drop_index(op.f("ix_work_day_overrides_status"), table_name="work_day_overrides")
    op.drop_table("work_day_overrides")
    op.drop_index(op.f("ix_employment_contracts_work_profile_id"), table_name="employment_contracts")
    op.drop_index(op.f("ix_employment_contracts_user_id"), table_name="employment_contracts")
    op.drop_index(op.f("ix_employment_contracts_effective_from"), table_name="employment_contracts")
    op.drop_table("employment_contracts")
    op.drop_index(op.f("ix_work_profiles_user_id"), table_name="work_profiles")
    op.drop_table("work_profiles")
