"""add catalog media and normalized item sources

Revision ID: 20260904_0042
Revises: 20260904_0041
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0042"
down_revision = "20260904_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "operation_item_templates",
        "shop_name_ci",
        existing_type=sa.String(length=255),
        type_=sa.String(length=320),
        existing_nullable=True,
    )
    op.create_table(
        "catalog_media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=32),
            nullable=False,
            server_default="image/webp",
        ),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("thumb_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("thumb_width", sa.Integer(), nullable=False),
        sa.Column("thumb_height", sa.Integer(), nullable=False),
        sa.Column("detail_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("detail_width", sa.Integer(), nullable=False),
        sa.Column("detail_height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_catalog_media_assets_user_id"),
        "catalog_media_assets",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "item_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_ci", sa.String(length=320), nullable=False),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["catalog_media_assets.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name_ci", name="uq_item_sources_user_name_ci"),
    )
    op.create_index(
        op.f("ix_item_sources_image_id"), "item_sources", ["image_id"], unique=False
    )
    op.create_index(
        op.f("ix_item_sources_name_ci"), "item_sources", ["name_ci"], unique=False
    )
    op.create_index(
        op.f("ix_item_sources_user_id"), "item_sources", ["user_id"], unique=False
    )

    op.add_column("item_brands", sa.Column("image_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_item_brands_image_id_catalog_media_assets",
        "item_brands",
        "catalog_media_assets",
        ["image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_item_brands_image_id"), "item_brands", ["image_id"], unique=False
    )

    op.add_column(
        "operation_item_templates", sa.Column("source_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "operation_item_templates", sa.Column("image_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_operation_item_templates_source_id_item_sources",
        "operation_item_templates",
        "item_sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_operation_item_templates_image_id_catalog_media_assets",
        "operation_item_templates",
        "catalog_media_assets",
        ["image_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_operation_item_templates_source_id"),
        "operation_item_templates",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_operation_item_templates_image_id"),
        "operation_item_templates",
        ["image_id"],
        unique=False,
    )

    # Prefer source labels already used by catalog positions, then add legacy
    # preference-only labels.  Stable ids let a rename update history without
    # copying logos or other metadata into every receipt row.
    op.execute(
        """
        INSERT INTO item_sources (user_id, name, name_ci, is_archived)
        SELECT DISTINCT ON (user_id, source_key)
               user_id, btrim(shop_name), source_key, false
        FROM (
            SELECT user_id,
                   shop_name,
                   coalesce(nullif(shop_name_ci, ''), lower(btrim(shop_name))) AS source_key,
                   id
            FROM operation_item_templates
            WHERE shop_name IS NOT NULL AND btrim(shop_name) <> ''
        ) AS candidates
        ORDER BY user_id, source_key, id
        ON CONFLICT (user_id, name_ci) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO item_sources (user_id, name, name_ci, is_archived)
        SELECT preferences.user_id,
               btrim(source_name),
               lower(btrim(source_name)),
               false
        FROM user_preferences AS preferences
        CROSS JOIN LATERAL json_array_elements_text(
            CASE
                WHEN json_typeof(preferences.data->'ui'->'item_catalog_sources') = 'array'
                THEN preferences.data->'ui'->'item_catalog_sources'
                ELSE '[]'::json
            END
        ) AS legacy(source_name)
        WHERE btrim(source_name) <> ''
        ON CONFLICT (user_id, name_ci) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE operation_item_templates AS template
        SET source_id = source.id
        FROM item_sources AS source
        WHERE source.user_id = template.user_id
          AND source.name_ci = coalesce(
              nullif(template.shop_name_ci, ''),
              lower(btrim(template.shop_name))
          )
        """
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_operation_item_templates_image_id"),
        table_name="operation_item_templates",
    )
    op.drop_index(
        op.f("ix_operation_item_templates_source_id"),
        table_name="operation_item_templates",
    )
    op.drop_constraint(
        "fk_operation_item_templates_image_id_catalog_media_assets",
        "operation_item_templates",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_operation_item_templates_source_id_item_sources",
        "operation_item_templates",
        type_="foreignkey",
    )
    op.drop_column("operation_item_templates", "image_id")
    op.drop_column("operation_item_templates", "source_id")

    op.drop_index(op.f("ix_item_brands_image_id"), table_name="item_brands")
    op.drop_constraint(
        "fk_item_brands_image_id_catalog_media_assets",
        "item_brands",
        type_="foreignkey",
    )
    op.drop_column("item_brands", "image_id")

    op.drop_index(op.f("ix_item_sources_user_id"), table_name="item_sources")
    op.drop_index(op.f("ix_item_sources_name_ci"), table_name="item_sources")
    op.drop_index(op.f("ix_item_sources_image_id"), table_name="item_sources")
    op.drop_table("item_sources")
    op.drop_index(
        op.f("ix_catalog_media_assets_user_id"), table_name="catalog_media_assets"
    )
    op.drop_table("catalog_media_assets")
    op.alter_column(
        "operation_item_templates",
        "shop_name_ci",
        existing_type=sa.String(length=320),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
