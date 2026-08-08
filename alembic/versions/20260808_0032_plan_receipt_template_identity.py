"""link plan receipt positions to catalog templates

Revision ID: 20260808_0032
Revises: 20260716_0031
Create Date: 2026-08-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260808_0032"
down_revision = "20260716_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plan_receipt_items", sa.Column("template_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_plan_receipt_items_template_id",
        "plan_receipt_items",
        "operation_item_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_plan_receipt_items_template_id",
        "plan_receipt_items",
        ["template_id"],
    )

    # A linked operation is the strongest legacy signal: it preserves the old
    # source text while already pointing at the template that may have moved.
    op.execute(
        """
        WITH operation_links AS (
            SELECT
                ori.user_id,
                lower(btrim(ori.name)) AS name_key,
                lower(btrim(coalesce(ori.shop_name, ''))) AS shop_key,
                min(ori.template_id) AS template_id
            FROM operation_receipt_items AS ori
            JOIN operation_item_templates AS template
              ON template.id = ori.template_id
             AND template.user_id = ori.user_id
             AND template.is_archived = false
            WHERE ori.template_id IS NOT NULL
            GROUP BY
                ori.user_id,
                lower(btrim(ori.name)),
                lower(btrim(coalesce(ori.shop_name, '')))
            HAVING count(DISTINCT ori.template_id) = 1
        )
        UPDATE plan_receipt_items AS plan_item
        SET template_id = operation_links.template_id
        FROM operation_links
        WHERE plan_item.template_id IS NULL
          AND plan_item.user_id = operation_links.user_id
          AND lower(btrim(plan_item.name)) = operation_links.name_key
          AND lower(btrim(coalesce(plan_item.shop_name, ''))) = operation_links.shop_key
        """
    )

    # Positions without operation history can still be linked by their current
    # exact catalog identity.
    op.execute(
        """
        WITH exact_matches AS (
            SELECT plan_item.id AS plan_item_id, min(template.id) AS template_id
            FROM plan_receipt_items AS plan_item
            JOIN operation_item_templates AS template
              ON template.user_id = plan_item.user_id
             AND template.is_archived = false
             AND template.name_ci = lower(btrim(plan_item.name))
             AND coalesce(template.shop_name_ci, '') = lower(btrim(coalesce(plan_item.shop_name, '')))
            WHERE plan_item.template_id IS NULL
            GROUP BY plan_item.id
            HAVING count(*) = 1
        )
        UPDATE plan_receipt_items AS plan_item
        SET template_id = exact_matches.template_id
        FROM exact_matches
        WHERE plan_item.id = exact_matches.plan_item_id
        """
    )

    # Last fallback: a unique active template name is unambiguous even if its
    # source was moved before plans gained template_id.
    op.execute(
        """
        WITH unique_names AS (
            SELECT user_id, name_ci, min(id) AS template_id
            FROM operation_item_templates
            WHERE is_archived = false
            GROUP BY user_id, name_ci
            HAVING count(*) = 1
        )
        UPDATE plan_receipt_items AS plan_item
        SET template_id = unique_names.template_id
        FROM unique_names
        WHERE plan_item.template_id IS NULL
          AND plan_item.user_id = unique_names.user_id
          AND lower(btrim(plan_item.name)) = unique_names.name_ci
        """
    )

    # Existing linked positions immediately follow the current active catalog
    # identity. Archived templates intentionally retain their stored snapshot.
    op.execute(
        """
        UPDATE operation_receipt_items AS receipt_item
        SET shop_name = template.shop_name,
            name = template.name
        FROM operation_item_templates AS template
        WHERE receipt_item.template_id = template.id
          AND receipt_item.user_id = template.user_id
          AND template.is_archived = false
        """
    )
    op.execute(
        """
        UPDATE plan_receipt_items AS receipt_item
        SET shop_name = template.shop_name,
            name = template.name
        FROM operation_item_templates AS template
        WHERE receipt_item.template_id = template.id
          AND receipt_item.user_id = template.user_id
          AND template.is_archived = false
        """
    )


def downgrade() -> None:
    op.drop_index("ix_plan_receipt_items_template_id", table_name="plan_receipt_items")
    op.drop_constraint("fk_plan_receipt_items_template_id", "plan_receipt_items", type_="foreignkey")
    op.drop_column("plan_receipt_items", "template_id")
