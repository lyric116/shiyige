from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.users import get_current_user
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.cart import Cart, CartItem
from backend.app.models.order import Order, OrderItem, PaymentRecord
from backend.app.models.product import ProductSku
from backend.app.models.user import User, UserAddress
from backend.app.schemas.order import CreateOrderRequest, PayOrderRequest
from backend.app.services.behavior import BEHAVIOR_CREATE_ORDER, BEHAVIOR_PAY_ORDER, log_behavior
from backend.app.services.cache import invalidate_recommendation_cache_for_user
from backend.app.services.member import accrue_points_for_paid_order
from backend.app.services.recommendation_logging import log_recommendation_action

router = APIRouter(prefix="/orders", tags=["orders"])


def build_cart_query(user_id: int):
    return (
        select(Cart)
        .options(
            selectinload(Cart.items).selectinload(CartItem.product),
            selectinload(Cart.items).selectinload(CartItem.sku),
        )
        .where(Cart.user_id == user_id)
    )


def build_order_query(order_id: int):
    return (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.sku).selectinload(ProductSku.inventory),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payment_records),
        )
        .where(Order.id == order_id)
    )


def serialize_order_item(item: OrderItem) -> dict[str, object]:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "sku_id": item.sku_id,
        "product_name": item.product_name,
        "sku_name": item.sku_name,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "unit_member_price": item.unit_member_price,
        "subtotal_amount": item.subtotal_amount,
    }


def serialize_order(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "goods_amount": order.goods_amount,
        "shipping_amount": order.shipping_amount,
        "payable_amount": order.payable_amount,
        "buyer_note": order.buyer_note,
        "address": {
            "recipient_name": order.recipient_name,
            "recipient_phone": order.recipient_phone,
            "recipient_region": order.recipient_region,
            "recipient_detail_address": order.recipient_detail_address,
            "recipient_postal_code": order.recipient_postal_code,
        },
        "items": [serialize_order_item(item) for item in order.items],
        "payment_records": [
            {
                "id": record.id,
                "payment_no": record.payment_no,
                "payment_method": record.payment_method,
                "amount": record.amount,
                "status": record.status,
                "paid_at": record.paid_at.isoformat() if record.paid_at else None,
            }
            for record in order.payment_records
        ],
        "created_at": order.created_at.isoformat(),
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
    }


def generate_order_no() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"SYG{timestamp[-14:]}"


def generate_payment_no() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"PAY{timestamp[-14:]}"


def load_user_address(db: Session, user_id: int, address_id: int) -> UserAddress:
    address = db.scalar(
        select(UserAddress).where(
            UserAddress.id == address_id,
            UserAddress.user_id == user_id,
        )
    )
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="address not found")
    return address


def load_existing_order_by_idempotency(
    db: Session,
    *,
    user_id: int,
    idempotency_key: str,
) -> Order | None:
    return db.scalar(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.sku).selectinload(ProductSku.inventory),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payment_records),
        )
        .where(Order.user_id == user_id, Order.idempotency_key == idempotency_key)
    )


def get_user_order(db: Session, *, user_id: int, order_id: int) -> Order | None:
    return db.scalar(build_order_query(order_id).where(Order.user_id == user_id))


@router.post("")
def create_order(
    payload: CreateOrderRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    idempotency_key = payload.idempotency_key.strip()
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency key is required",
        )

    existing_order = load_existing_order_by_idempotency(
        db,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
    )
    if existing_order is not None:
        return build_response(
            request=request,
            code=0,
            message="order exists",
            data={"order": serialize_order(existing_order)},
            status_code=200,
        )

    address = load_user_address(db, current_user.id, payload.address_id)
    cart = db.scalar(build_cart_query(current_user.id))
    if cart is None or not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart is empty")

    goods_amount = Decimal("0.00")
    order = Order(
        order_no=generate_order_no(),
        user_id=current_user.id,
        status="PENDING_PAYMENT",
        goods_amount=Decimal("0.00"),
        shipping_amount=Decimal("10.00"),
        payable_amount=Decimal("0.00"),
        recipient_name=address.recipient_name,
        recipient_phone=address.phone,
        recipient_region=address.region,
        recipient_detail_address=address.detail_address,
        recipient_postal_code=address.postal_code,
        buyer_note=payload.buyer_note.strip() if payload.buyer_note else None,
        idempotency_key=idempotency_key,
    )

    for cart_item in cart.items:
        sku = cart_item.sku
        product = cart_item.product
        if sku is None or product is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="cart item unavailable",
            )

        subtotal_amount = sku.price * cart_item.quantity
        goods_amount += subtotal_amount
        order.items.append(
            OrderItem(
                product_id=product.id,
                sku_id=sku.id,
                product_name=product.name,
                sku_name=sku.name,
                quantity=cart_item.quantity,
                unit_price=sku.price,
                unit_member_price=sku.member_price,
                subtotal_amount=subtotal_amount,
            )
        )

    order.goods_amount = goods_amount
    order.payable_amount = goods_amount + order.shipping_amount

    db.add(order)
    db.flush()
    log_behavior(
        db,
        user=current_user,
        behavior_type=BEHAVIOR_CREATE_ORDER,
        target_id=order.id,
        target_type="order",
        ext_json={
            "order_no": order.order_no,
            "item_count": len(order.items),
            "payable_amount": str(order.payable_amount),
            "product_ids": [item.product_id for item in order.items],
        },
    )
    for item in order.items:
        log_recommendation_action(
            db,
            user_id=current_user.id,
            product_id=item.product_id,
            action_type="create_order",
            order_id=order.id,
        )
    for cart_item in list(cart.items):
        db.delete(cart_item)
    invalidate_recommendation_cache_for_user(current_user.id)
    db.commit()
    db.expire_all()

    created_order = db.scalar(build_order_query(order.id))
    assert created_order is not None

    return build_response(
        request=request,
        code=0,
        message="order created",
        data={"order": serialize_order(created_order)},
        status_code=201,
    )


@router.post("/{order_id}/pay")
def pay_order(
    order_id: int,
    payload: PayOrderRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment_method = payload.payment_method.strip().lower()
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment method is required",
        )

    order = get_user_order(db, user_id=current_user.id, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
    if order.status != "PENDING_PAYMENT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="order status invalid")

    inventory_snapshots: list[tuple[OrderItem, ProductSku]] = []
    for item in order.items:
        sku = item.sku
        if sku is None or not sku.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sku unavailable")
        if sku.inventory is None or sku.inventory.quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="inventory insufficient",
            )
        inventory_snapshots.append((item, sku))

    paid_at = datetime.now(UTC)
    for item, sku in inventory_snapshots:
        sku.inventory.quantity -= item.quantity
        db.add(sku.inventory)

    order.status = "PAID"
    order.paid_at = paid_at
    db.add(order)
    payment_record = PaymentRecord(
        order_id=order.id,
        payment_no=generate_payment_no(),
        payment_method=payment_method,
        amount=order.payable_amount,
        status="PAID",
        paid_at=paid_at,
    )
    db.add(payment_record)
    accrue_points_for_paid_order(
        db,
        user_id=current_user.id,
        order=order,
        payment_record=payment_record,
    )
    log_behavior(
        db,
        user=current_user,
        behavior_type=BEHAVIOR_PAY_ORDER,
        target_id=order.id,
        target_type="order",
        ext_json={
            "order_no": order.order_no,
            "payment_method": payment_method,
            "payable_amount": str(order.payable_amount),
            "product_ids": [item.product_id for item in order.items],
        },
    )
    for item in order.items:
        log_recommendation_action(
            db,
            user_id=current_user.id,
            product_id=item.product_id,
            action_type="pay_order",
            order_id=order.id,
        )
    invalidate_recommendation_cache_for_user(current_user.id)
    db.commit()
    db.expire_all()

    paid_order = get_user_order(db, user_id=current_user.id, order_id=order_id)
    assert paid_order is not None
    return build_response(
        request=request,
        code=0,
        message="order paid",
        data={"order": serialize_order(paid_order)},
        status_code=200,
    )


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = get_user_order(db, user_id=current_user.id, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
    if order.status == "PAID":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="paid order cannot be cancelled",
        )
    if order.status == "CANCELLED":
        return build_response(
            request=request,
            code=0,
            message="order cancelled",
            data={"order": serialize_order(order)},
            status_code=200,
        )

    order.status = "CANCELLED"
    order.cancelled_at = datetime.now(UTC)
    db.add(order)
    db.commit()
    db.expire_all()

    cancelled_order = get_user_order(db, user_id=current_user.id, order_id=order_id)
    assert cancelled_order is not None
    return build_response(
        request=request,
        code=0,
        message="order cancelled",
        data={"order": serialize_order(cancelled_order)},
        status_code=200,
    )


@router.get("")
def list_orders(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    orders = db.scalars(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.sku).selectinload(ProductSku.inventory),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payment_records),
        )
        .where(Order.user_id == current_user.id)
        .order_by(Order.id.desc())
    ).all()

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"items": [serialize_order(order) for order in orders]},
        status_code=200,
    )


@router.get("/{order_id}")
def get_order_detail(
    order_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = get_user_order(db, user_id=current_user.id, order_id=order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"order": serialize_order(order)},
        status_code=200,
    )
