from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.users import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.cart import Cart, CartItem
from backend.app.models.product import Product, ProductSku
from backend.app.models.user import User
from backend.app.schemas.cart import AddCartItemRequest, UpdateCartItemRequest
from backend.app.services.behavior import BEHAVIOR_ADD_TO_CART, log_behavior
from backend.app.services.cache import invalidate_recommendation_cache_for_user
from backend.app.services.recommendation_logging import log_recommendation_action

router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_query(user_id: int):
    return (
        select(Cart)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.product)
            .selectinload(Product.category),
            selectinload(Cart.items).selectinload(CartItem.sku),
        )
        .where(Cart.user_id == user_id)
    )


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.scalar(get_cart_query(user_id))
    if cart is not None:
        return cart

    cart = Cart(user_id=user_id)
    db.add(cart)
    db.flush()
    db.refresh(cart)
    return cart


def serialize_cart_item(item: CartItem) -> dict[str, object]:
    sku = item.sku
    price = sku.price if sku is not None else Decimal("0")
    return {
        "id": item.id,
        "quantity": item.quantity,
        "product": {
            "id": item.product.id,
            "name": item.product.name,
            "cover_url": item.product.cover_url,
            "category": item.product.category.name if item.product.category else None,
        },
        "sku": {
            "id": sku.id if sku else None,
            "sku_code": sku.sku_code if sku else None,
            "name": sku.name if sku else None,
            "price": price,
            "member_price": sku.member_price if sku else None,
        },
        "subtotal": price * item.quantity,
    }


def serialize_cart(cart: Cart | None) -> dict[str, object]:
    if cart is None:
        return {
            "id": None,
            "items": [],
            "total_quantity": 0,
            "total_amount": Decimal("0.00"),
        }

    items = [serialize_cart_item(item) for item in cart.items]
    total_quantity = sum(item.quantity for item in cart.items)
    total_amount = sum((item["subtotal"] for item in items), Decimal("0.00"))

    return {
        "id": cart.id,
        "items": items,
        "total_quantity": total_quantity,
        "total_amount": total_amount,
    }


def validate_quantity(quantity: int) -> None:
    if quantity < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity is invalid")


def load_product_for_cart(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    if product.status != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product unavailable")
    return product


def load_sku_for_cart(db: Session, product_id: int, sku_id: int) -> ProductSku:
    sku = db.scalar(
        select(ProductSku).where(
            ProductSku.id == sku_id,
            ProductSku.product_id == product_id,
        )
    )
    if sku is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sku not found")
    if not sku.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sku unavailable")
    if sku.inventory is None or sku.inventory.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="inventory insufficient")
    return sku


def ensure_inventory(quantity: int, sku: ProductSku) -> None:
    inventory_quantity = sku.inventory.quantity if sku.inventory else 0
    if quantity > inventory_quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="inventory insufficient")


def get_cart_item_for_user(db: Session, user_id: int, item_id: int) -> CartItem | None:
    return db.scalar(
        select(CartItem)
        .join(Cart, CartItem.cart_id == Cart.id)
        .options(
            selectinload(CartItem.product).selectinload(Product.category),
            selectinload(CartItem.sku),
        )
        .where(Cart.user_id == user_id, CartItem.id == item_id)
    )


@router.get("")
def get_cart(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cart = db.scalar(get_cart_query(current_user.id))
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"cart": serialize_cart(cart)},
        status_code=200,
    )


@router.post("/items")
def add_cart_item(
    payload: AddCartItemRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    validate_quantity(payload.quantity)
    product = load_product_for_cart(db, payload.product_id)
    sku = load_sku_for_cart(db, payload.product_id, payload.sku_id)

    cart = get_or_create_cart(db, current_user.id)
    existing_item = db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.sku_id == payload.sku_id)
    )

    if existing_item is not None:
        new_quantity = existing_item.quantity + payload.quantity
        ensure_inventory(new_quantity, sku)
        existing_item.quantity = new_quantity
        cart_item = existing_item
    else:
        ensure_inventory(payload.quantity, sku)
        cart_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            sku_id=sku.id,
            quantity=payload.quantity,
        )
        db.add(cart_item)

    log_behavior(
        db,
        user=current_user,
        behavior_type=BEHAVIOR_ADD_TO_CART,
        target_id=product.id,
        target_type="product",
        ext_json={
            "sku_id": sku.id,
            "quantity": cart_item.quantity,
            "cart_id": cart.id,
        },
    )
    log_recommendation_action(
        db,
        user_id=current_user.id,
        product_id=product.id,
        action_type="add_to_cart",
    )
    invalidate_recommendation_cache_for_user(current_user.id)
    db.commit()
    db.expire_all()
    cart = db.scalar(get_cart_query(current_user.id))
    cart_item = next(item for item in cart.items if item.sku_id == sku.id)

    return build_response(
        request=request,
        code=0,
        message="cart item added",
        data={"item": serialize_cart_item(cart_item), "cart": serialize_cart(cart)},
        status_code=201,
    )


@router.put("/items/{item_id}")
def update_cart_item(
    item_id: int,
    payload: UpdateCartItemRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    validate_quantity(payload.quantity)
    item = get_cart_item_for_user(db, current_user.id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")

    if item.product.status != 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="product unavailable")
    if item.sku is None or not item.sku.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sku unavailable")

    ensure_inventory(payload.quantity, item.sku)
    item.quantity = payload.quantity
    db.add(item)
    db.commit()
    db.expire_all()

    cart = db.scalar(get_cart_query(current_user.id))
    updated_item = next(cart_item for cart_item in cart.items if cart_item.id == item_id)

    return build_response(
        request=request,
        code=0,
        message="cart item updated",
        data={"item": serialize_cart_item(updated_item), "cart": serialize_cart(cart)},
        status_code=200,
    )


@router.delete("/items/{item_id}")
def delete_cart_item(
    item_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = get_cart_item_for_user(db, current_user.id, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cart item not found")

    db.delete(item)
    db.commit()
    db.expire_all()

    cart = db.scalar(get_cart_query(current_user.id))
    return build_response(
        request=request,
        code=0,
        message="cart item deleted",
        data={"cart": serialize_cart(cart)},
        status_code=200,
    )
