from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.admin_auth import create_operation_log, get_current_admin
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.models.product import Category, Inventory, Product, ProductMedia, ProductSku, ProductTag
from backend.app.schemas.admin import AdminProductUpsertRequest


router = APIRouter(prefix="/admin/products", tags=["admin-products"])


def build_admin_product_query():
    return (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.media_items),
            selectinload(Product.tags),
        )
        .order_by(Product.id.desc())
    )


def serialize_admin_product(product: Product) -> dict[str, object]:
    default_sku = product.default_sku
    return {
        "id": product.id,
        "category": {
            "id": product.category.id,
            "name": product.category.name,
            "slug": product.category.slug,
        },
        "name": product.name,
        "subtitle": product.subtitle,
        "cover_url": product.cover_url,
        "description": product.description,
        "culture_summary": product.culture_summary,
        "dynasty_style": product.dynasty_style,
        "craft_type": product.craft_type,
        "festival_tag": product.festival_tag,
        "scene_tag": product.scene_tag,
        "status": product.status,
        "tags": [tag.tag for tag in sorted(product.tags, key=lambda item: item.id)],
        "media_urls": [media.url for media in sorted(product.media_items, key=lambda item: (item.sort_order, item.id))],
        "default_sku": (
            {
                "id": default_sku.id,
                "sku_code": default_sku.sku_code,
                "name": default_sku.name,
                "price": default_sku.price,
                "member_price": default_sku.member_price,
                "inventory": default_sku.inventory.quantity if default_sku.inventory else 0,
                "is_active": default_sku.is_active,
            }
            if default_sku is not None
            else None
        ),
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def get_category_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    return category


def ensure_unique_sku_code(db: Session, sku_code: str, current_sku_id: int | None = None) -> None:
    query = select(ProductSku).where(ProductSku.sku_code == sku_code)
    if current_sku_id is not None:
        query = query.where(ProductSku.id != current_sku_id)

    existing_sku = db.scalar(query)
    if existing_sku is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sku code already exists")


def apply_product_payload(db: Session, product: Product, payload: AdminProductUpsertRequest) -> None:
    category = get_category_or_404(db, payload.category_id)
    default_sku = product.default_sku
    ensure_unique_sku_code(db, payload.default_sku.sku_code.strip(), default_sku.id if default_sku else None)

    product.category = category
    product.name = payload.name.strip()
    product.subtitle = normalize_optional_text(payload.subtitle)
    product.cover_url = normalize_optional_text(payload.cover_url)
    product.description = normalize_optional_text(payload.description)
    product.culture_summary = normalize_optional_text(payload.culture_summary)
    product.dynasty_style = normalize_optional_text(payload.dynasty_style)
    product.craft_type = normalize_optional_text(payload.craft_type)
    product.festival_tag = normalize_optional_text(payload.festival_tag)
    product.scene_tag = normalize_optional_text(payload.scene_tag)
    product.status = payload.status

    normalized_tags = []
    for tag in payload.tags:
        cleaned_tag = tag.strip()
        if cleaned_tag and cleaned_tag not in normalized_tags:
            normalized_tags.append(cleaned_tag)

    product.tags.clear()
    for tag in normalized_tags:
        product.tags.append(ProductTag(tag=tag))

    normalized_media_urls = []
    for media_url in payload.media_urls:
        cleaned_media_url = media_url.strip()
        if cleaned_media_url:
            normalized_media_urls.append(cleaned_media_url)

    product.media_items.clear()
    for index, media_url in enumerate(normalized_media_urls, start=1):
        product.media_items.append(
            ProductMedia(
                media_type="image",
                url=media_url,
                sort_order=index,
            )
        )

    if product.cover_url is None and normalized_media_urls:
        product.cover_url = normalized_media_urls[0]

    if default_sku is None:
        default_sku = ProductSku(is_default=True)
        product.skus.append(default_sku)

    for sku in product.skus:
        sku.is_default = sku is default_sku

    default_sku.sku_code = payload.default_sku.sku_code.strip()
    default_sku.name = payload.default_sku.name.strip()
    default_sku.price = payload.default_sku.price
    default_sku.member_price = payload.default_sku.member_price
    default_sku.is_active = payload.default_sku.is_active

    if default_sku.inventory is None:
        default_sku.inventory = Inventory(quantity=payload.default_sku.inventory)
    else:
        default_sku.inventory.quantity = payload.default_sku.inventory


@router.get("")
def list_products(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = None,
    category_id: int | None = None,
    status_value: int | None = Query(default=None, alias="status"),
):
    query = build_admin_product_query()

    if q:
        keyword = f"%{q.strip()}%"
        query = query.where(Product.name.ilike(keyword))

    if category_id is not None:
        query = query.where(Product.category_id == category_id)

    if status_value is not None:
        query = query.where(Product.status == status_value)

    products = db.scalars(query).unique().all()
    total = len(products)
    start = (page - 1) * page_size
    end = start + page_size

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "items": [serialize_admin_product(product) for product in products[start:end]],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        status_code=200,
    )


@router.post("")
def create_product(
    payload: AdminProductUpsertRequest,
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = Product(category_id=payload.category_id)
    apply_product_payload(db, product, payload)
    db.add(product)
    db.flush()
    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_product_create",
        target_type="product",
        target_id=product.id,
        detail_json={"name": product.name},
    )
    db.commit()

    created_product = db.scalar(build_admin_product_query().where(Product.id == product.id))
    assert created_product is not None
    return build_response(
        request=request,
        code=0,
        message="product created",
        data={"product": serialize_admin_product(created_product)},
        status_code=201,
    )


@router.put("/{product_id}")
def update_product(
    product_id: int,
    payload: AdminProductUpsertRequest,
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    product = db.scalar(build_admin_product_query().where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")

    apply_product_payload(db, product, payload)
    db.add(product)
    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_product_update",
        target_type="product",
        target_id=product.id,
        detail_json={"name": product.name},
    )
    db.commit()

    updated_product = db.scalar(build_admin_product_query().where(Product.id == product_id))
    assert updated_product is not None
    return build_response(
        request=request,
        code=0,
        message="product updated",
        data={"product": serialize_admin_product(updated_product)},
        status_code=200,
    )
