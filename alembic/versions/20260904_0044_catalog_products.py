"""add canonical catalog products above source-specific offers

Revision ID: 20260904_0044
Revises: 20260904_0043
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_0044"
down_revision = "20260904_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_ci", sa.String(length=320), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("image_id", sa.Integer(), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
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
            ["brand_id"], ["item_brands.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["catalog_media_assets.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_catalog_products_user_id"),
        "catalog_products",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_products_name_ci"),
        "catalog_products",
        ["name_ci"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_products_brand_id"),
        "catalog_products",
        ["brand_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_products_category_id"),
        "catalog_products",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catalog_products_image_id"),
        "catalog_products",
        ["image_id"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_products_user_name_ci",
        "catalog_products",
        ["user_id", "name_ci"],
        unique=False,
    )

    op.add_column(
        "operation_item_templates",
        sa.Column("product_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_operation_item_templates_product_id_catalog_products",
        "operation_item_templates",
        "catalog_products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_operation_item_templates_product_id"),
        "operation_item_templates",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_operation_item_templates_product_source",
        "operation_item_templates",
        ["product_id", "source_id"],
        unique=False,
    )
    op.create_index(
        "ix_operation_item_templates_user_product",
        "operation_item_templates",
        ["user_id", "product_id"],
        unique=False,
    )

    # Keep every legacy catalog position intact. Each becomes one offer of a
    # newly-created product; potentially equal products are deliberately left
    # separate until the user confirms a merge.
    connection = op.get_bind()
    legacy_templates = sa.table(
        "operation_item_templates",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("name", sa.Text()),
        sa.column("name_ci", sa.String(length=320)),
        sa.column("brand_id", sa.Integer()),
        sa.column("last_category_id", sa.Integer()),
        sa.column("image_id", sa.Integer()),
        sa.column("is_archived", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("product_id", sa.Integer()),
    )
    products = sa.table(
        "catalog_products",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
        sa.column("name", sa.Text()),
        sa.column("name_ci", sa.String(length=320)),
        sa.column("brand_id", sa.Integer()),
        sa.column("category_id", sa.Integer()),
        sa.column("image_id", sa.Integer()),
        sa.column("is_archived", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    rows = list(
        connection.execute(
            sa.select(
                legacy_templates.c.id,
                legacy_templates.c.user_id,
                legacy_templates.c.name,
                legacy_templates.c.name_ci,
                legacy_templates.c.brand_id,
                legacy_templates.c.last_category_id,
                legacy_templates.c.image_id,
                legacy_templates.c.is_archived,
                legacy_templates.c.created_at,
                legacy_templates.c.updated_at,
            ).order_by(legacy_templates.c.id)
        ).mappings()
    )
    for row in rows:
        product_id = connection.scalar(
            sa.insert(products)
            .values(
                user_id=row["user_id"],
                name=row["name"],
                name_ci=row["name_ci"],
                brand_id=row["brand_id"],
                category_id=row["last_category_id"],
                image_id=row["image_id"],
                is_archived=row["is_archived"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            .returning(products.c.id)
        )
        if product_id is None:
            raise RuntimeError("Failed to backfill catalog product")
        connection.execute(
            sa.update(legacy_templates)
            .where(legacy_templates.c.id == row["id"])
            .values(product_id=int(product_id))
        )


def downgrade() -> None:
    op.drop_index(
        "ix_operation_item_templates_user_product",
        table_name="operation_item_templates",
    )
    op.drop_index(
        "ix_operation_item_templates_product_source",
        table_name="operation_item_templates",
    )
    op.drop_index(
        op.f("ix_operation_item_templates_product_id"),
        table_name="operation_item_templates",
    )
    op.drop_constraint(
        "fk_operation_item_templates_product_id_catalog_products",
        "operation_item_templates",
        type_="foreignkey",
    )
    op.drop_column("operation_item_templates", "product_id")

    op.drop_index("ix_catalog_products_user_name_ci", table_name="catalog_products")
    op.drop_index(op.f("ix_catalog_products_image_id"), table_name="catalog_products")
    op.drop_index(op.f("ix_catalog_products_category_id"), table_name="catalog_products")
    op.drop_index(op.f("ix_catalog_products_brand_id"), table_name="catalog_products")
    op.drop_index(op.f("ix_catalog_products_name_ci"), table_name="catalog_products")
    op.drop_index(op.f("ix_catalog_products_user_id"), table_name="catalog_products")
    op.drop_table("catalog_products")
