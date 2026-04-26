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

SYNTHETIC_NAME_PREFIX = "Synthetic "
SYNTHETIC_MEDIA_PER_PRODUCT = 2


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


def parse_synthetic_product_name(name: str) -> tuple[int, str] | None:
    if not name.startswith(SYNTHETIC_NAME_PREFIX):
        return None

    parts = name.split(" ", 2)
    if len(parts) != 3:
        return None

    try:
        synthetic_index = int(parts[1])
    except ValueError:
        return None

    return synthetic_index, parts[2]


def build_template_media_pool(template: Product) -> list[str]:
    ordered_media = sorted(template.media_items, key=lambda item: (item.sort_order, item.id))
    pool: list[str] = []
    seen: set[str] = set()

    for media in ordered_media:
        if media.url and media.url not in seen:
            pool.append(media.url)
            seen.add(media.url)

    if template.cover_url and template.cover_url not in seen:
        pool.insert(0, template.cover_url)

    return pool


def select_synthetic_media_urls(*, template: Product, rotation_index: int) -> list[str]:
    pool = build_template_media_pool(template)
    if not pool:
        return []

    if len(pool) == 1:
        return pool

    start = rotation_index % len(pool)
    selected_count = min(SYNTHETIC_MEDIA_PER_PRODUCT, len(pool))
    return [pool[(start + offset) % len(pool)] for offset in range(selected_count)]


def assign_product_media(
    product: Product,
    *,
    cover_url: str | None,
    media_urls: list[str],
) -> None:
    product.cover_url = cover_url
    product.media_items = [
        ProductMedia(media_type="image", url=media_url, sort_order=media_index)
        for media_index, media_url in enumerate(media_urls, start=1)
    ]


def sync_synthetic_product_assets(
    product: Product,
    *,
    template: Product,
    rotation_index: int,
) -> bool:
    media_urls = select_synthetic_media_urls(
        template=template,
        rotation_index=rotation_index,
    )
    target_cover_url = media_urls[0] if media_urls else template.cover_url
    existing_media_urls = [
        media.url
        for media in sorted(
            product.media_items,
            key=lambda item: (item.sort_order, item.id),
        )
    ]

    if product.cover_url == target_cover_url and existing_media_urls == media_urls:
        return False

    assign_product_media(
        product,
        cover_url=target_cover_url,
        media_urls=media_urls,
    )
    return True


def count_existing_synthetic_products(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    synthetic_names = session.scalars(
        select(Product.name)
        .where(Product.name.like("Synthetic %"))
        .order_by(Product.id.asc())
    ).all()

    for name in synthetic_names:
        parsed_name = parse_synthetic_product_name(name)
        if parsed_name is None:
            continue

        _, template_name = parsed_name
        counts[template_name] = counts.get(template_name, 0) + 1

    return counts


def resync_synthetic_catalog_assets(
    session: Session,
    *,
    seed_products: list[Product],
) -> int:
    templates_by_name = {product.name: product for product in seed_products}
    synthetic_products = (
        session.scalars(
            select(Product)
            .options(selectinload(Product.media_items))
            .where(Product.name.like("Synthetic %"))
            .order_by(Product.id.asc())
        )
        .unique()
        .all()
    )

    updated = 0
    rotation_counts: dict[str, int] = {}
    for product in synthetic_products:
        parsed_name = parse_synthetic_product_name(product.name)
        if parsed_name is None:
            continue

        _, template_name = parsed_name
        template = templates_by_name.get(template_name)
        if template is None:
            continue

        rotation_index = rotation_counts.get(template_name, 0)
        if sync_synthetic_product_assets(
            product,
            template=template,
            rotation_index=rotation_index,
        ):
            updated += 1
        rotation_counts[template_name] = rotation_index + 1

    return updated


def ensure_synthetic_catalog(
    session: Session,
    *,
    target_products: int,
) -> dict[str, int]:
    seed_base_data(session)
    seed_products = load_seed_products(session)
    current_count = int(session.scalar(select(func.count()).select_from(Product)) or 0)
    if current_count >= target_products:
        updated_products = resync_synthetic_catalog_assets(
            session,
            seed_products=seed_products,
        )
        session.commit()
        return {
            "existing_products": current_count,
            "created_products": 0,
            "target_products": target_products,
            "updated_products": updated_products,
        }

    created = 0
    next_index = current_count + 1
    synthetic_counts = count_existing_synthetic_products(session)
    while current_count + created < target_products:
        template = seed_products[created % len(seed_products)]
        rotation_index = synthetic_counts.get(template.name, 0)
        created += 1
        clone_product(
            session,
            template=template,
            synthetic_index=next_index,
            rotation_index=rotation_index,
        )
        synthetic_counts[template.name] = rotation_index + 1
        next_index += 1

    updated_products = resync_synthetic_catalog_assets(
        session,
        seed_products=seed_products,
    )
    session.commit()
    return {
        "existing_products": current_count,
        "created_products": created,
        "target_products": target_products,
        "updated_products": updated_products,
    }


def clone_product(
    session: Session,
    *,
    template: Product,
    synthetic_index: int,
    rotation_index: int,
) -> None:
    product = Product(
        category_id=template.category_id,
        name=f"Synthetic {synthetic_index:06d} {template.name}",
        subtitle=template.subtitle,
        cover_url=None,
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
    media_urls = select_synthetic_media_urls(
        template=template,
        rotation_index=rotation_index,
    )
    assign_product_media(
        product,
        cover_url=media_urls[0] if media_urls else template.cover_url,
        media_urls=media_urls,
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
