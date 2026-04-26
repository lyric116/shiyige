from __future__ import annotations
# ruff: noqa: E402, I001

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.database import get_session_factory
from backend.app.models.base import Base
from backend.app.models.product import Inventory, Product, ProductMedia, ProductSku, ProductTag
from backend.scripts.seed_base_data import seed_base_data


def load_seed_products(session: Session) -> list[Product]:
    return (
        session.scalars(
            select(Product)
            .options(
                selectinload(Product.tags),
                selectinload(Product.media_items),
                selectinload(Product.skus).selectinload(ProductSku.inventory),
            )
            .where(Product.name.not_like("Synthetic %"))
            .order_by(Product.id.asc())
        )
        .unique()
        .all()
    )


def ensure_synthetic_catalog(
    session: Session,
    *,
    target_products: int,
) -> dict[str, int]:
    seed_base_data(session)
    current_count = int(session.scalar(select(func.count()).select_from(Product)) or 0)
    if current_count >= target_products:
        return {
            "existing_products": current_count,
            "created_products": 0,
            "target_products": target_products,
        }

    seed_products = load_seed_products(session)
    created = 0
    next_index = current_count + 1
    while current_count + created < target_products:
        template = seed_products[created % len(seed_products)]
        created += 1
        clone_product(session, template=template, synthetic_index=next_index)
        next_index += 1

    session.commit()
    return {
        "existing_products": current_count,
        "created_products": created,
        "target_products": target_products,
    }


def clone_product(
    session: Session,
    *,
    template: Product,
    synthetic_index: int,
) -> None:
    product = Product(
        category_id=template.category_id,
        name=f"Synthetic {synthetic_index:06d} {template.name}",
        subtitle=template.subtitle,
        cover_url=template.cover_url,
        description=template.description,
        culture_summary=template.culture_summary,
        dynasty_style=template.dynasty_style,
        craft_type=template.craft_type,
        festival_tag=template.festival_tag,
        scene_tag=template.scene_tag,
        status=template.status,
    )
    session.add(product)
    session.flush()

    for media in template.media_items:
        session.add(
            ProductMedia(
                product_id=product.id,
                media_type=media.media_type,
                url=media.url,
                sort_order=media.sort_order,
            )
        )

    for tag in template.tags:
        session.add(ProductTag(product_id=product.id, tag=tag.tag))

    default_sku = template.default_sku
    if default_sku is None:
        return

    price = Decimal(default_sku.price)
    member_price = Decimal(default_sku.member_price or default_sku.price)
    sku = ProductSku(
        product_id=product.id,
        sku_code=f"SYN-{synthetic_index:06d}",
        name=f"{default_sku.name} 合成款",
        specs_json=dict(default_sku.specs_json or {}),
        price=price,
        member_price=member_price,
        is_default=True,
        is_active=True,
    )
    session.add(sku)
    session.flush()

    inventory = Inventory(
        sku_id=sku.id,
        quantity=max(default_sku.inventory.quantity if default_sku.inventory else 10, 5),
    )
    session.add(inventory)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic catalog records")
    parser.add_argument("--products", type=int, default=1000, help="Target total product count")
    args = parser.parse_args()

    session = get_session_factory()()
    try:
        Base.metadata.create_all(bind=session.get_bind())
        result = ensure_synthetic_catalog(session, target_products=args.products)
        print(result)
    finally:
        session.close()


if __name__ == "__main__":
    main()
