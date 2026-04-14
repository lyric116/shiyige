from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.database import get_session_factory
from backend.app.core.security import hash_password
from backend.app.models.membership import PointAccount
from backend.app.models.order import Order, OrderItem, PaymentRecord
from backend.app.models.product import Product, ProductSku
from backend.app.models.recommendation import UserInterestProfile
from backend.app.models.user import User, UserAddress, UserBehaviorLog, UserProfile
from backend.app.services.member import accrue_points_for_paid_order
from backend.app.services.recommendations import build_user_interest_profile
from backend.scripts.seed_base_data import seed_base_data


DEMO_USER_EMAIL = "user@shiyige-demo.com"
DEMO_USER_USERNAME = "demo-user"
DEMO_USER_PASSWORD = "user123456"
DEMO_USER_DISPLAY_NAME = "拾遗演示用户"

DEMO_ADDRESS = {
    "recipient_name": "拾遗演示用户",
    "phone": "13800138000",
    "region": "北京市 东城区",
    "detail_address": "景山前街 4 号",
    "postal_code": "100009",
}

DEMO_PAID_ORDER_KEY = "demo-paid-order"
DEMO_PENDING_ORDER_KEY = "demo-pending-order"

DEMO_PAID_PRODUCT_NAME = "明制襦裙"
DEMO_PENDING_PRODUCT_NAME = "故宫宫廷香囊"


def generate_order_no() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"SYG{timestamp[-14:]}"


def generate_payment_no() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"PAY{timestamp[-14:]}"


def load_product_with_default_sku(session: Session, product_name: str) -> tuple[Product, ProductSku]:
    product = session.scalar(
        select(Product)
        .options(selectinload(Product.skus).selectinload(ProductSku.inventory))
        .where(Product.name == product_name)
    )
    if product is None:
        raise RuntimeError(f"seed product not found: {product_name}")

    default_sku = product.default_sku
    if default_sku is None or default_sku.inventory is None:
        raise RuntimeError(f"default sku missing inventory for product: {product_name}")

    return product, default_sku


def ensure_demo_user(session: Session) -> tuple[User, UserAddress]:
    user = session.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None:
        user = User(
            email=DEMO_USER_EMAIL,
            username=DEMO_USER_USERNAME,
            password_hash=hash_password(DEMO_USER_PASSWORD),
            role="user",
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user.username = DEMO_USER_USERNAME
        user.password_hash = hash_password(DEMO_USER_PASSWORD)
        user.role = "user"
        user.is_active = True

    if user.profile is None:
        user.profile = UserProfile(display_name=DEMO_USER_DISPLAY_NAME)
    else:
        user.profile.display_name = DEMO_USER_DISPLAY_NAME

    for existing_address in user.addresses:
        existing_address.is_default = False

    address = session.scalar(
        select(UserAddress).where(
            UserAddress.user_id == user.id,
            UserAddress.detail_address == DEMO_ADDRESS["detail_address"],
        )
    )
    if address is None:
        address = UserAddress(user_id=user.id, is_default=True, **DEMO_ADDRESS)
        session.add(address)
        session.flush()
    else:
        address.recipient_name = DEMO_ADDRESS["recipient_name"]
        address.phone = DEMO_ADDRESS["phone"]
        address.region = DEMO_ADDRESS["region"]
        address.detail_address = DEMO_ADDRESS["detail_address"]
        address.postal_code = DEMO_ADDRESS["postal_code"]
        address.is_default = True

    session.flush()
    return user, address


def ensure_demo_order(
    session: Session,
    *,
    user: User,
    address: UserAddress,
    product_name: str,
    quantity: int,
    idempotency_key: str,
    status: str,
    buyer_note: str,
    payment_method: str | None = None,
) -> tuple[Order, Product, ProductSku]:
    existing_order = session.scalar(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.payment_records),
        )
        .where(Order.user_id == user.id, Order.idempotency_key == idempotency_key)
    )
    if existing_order is not None:
        product, sku = load_product_with_default_sku(session, product_name)
        return existing_order, product, sku

    product, sku = load_product_with_default_sku(session, product_name)
    if status == "PAID" and sku.inventory.quantity < quantity:
        raise RuntimeError(f"not enough inventory to seed demo paid order for {product_name}")

    subtotal_amount = Decimal(sku.price) * quantity
    shipping_amount = Decimal("10.00")
    payable_amount = subtotal_amount + shipping_amount

    order = Order(
        order_no=generate_order_no(),
        user_id=user.id,
        status=status,
        goods_amount=subtotal_amount,
        shipping_amount=shipping_amount,
        payable_amount=payable_amount,
        recipient_name=address.recipient_name,
        recipient_phone=address.phone,
        recipient_region=address.region,
        recipient_detail_address=address.detail_address,
        recipient_postal_code=address.postal_code,
        buyer_note=buyer_note,
        idempotency_key=idempotency_key,
    )
    order.items.append(
        OrderItem(
            product_id=product.id,
            sku_id=sku.id,
            product_name=product.name,
            sku_name=sku.name,
            quantity=quantity,
            unit_price=sku.price,
            unit_member_price=sku.member_price,
            subtotal_amount=subtotal_amount,
        )
    )
    session.add(order)
    session.flush()

    if status == "PAID":
        paid_at = datetime.utcnow()
        order.paid_at = paid_at
        sku.inventory.quantity -= quantity
        session.add(sku.inventory)

        payment_record = PaymentRecord(
            order_id=order.id,
            payment_no=generate_payment_no(),
            payment_method=payment_method or "alipay",
            amount=payable_amount,
            status="PAID",
            paid_at=paid_at,
        )
        session.add(payment_record)
        session.flush()
        accrue_points_for_paid_order(
            session,
            user_id=user.id,
            order=order,
            payment_record=payment_record,
        )

    session.flush()
    return order, product, sku


def ensure_demo_behavior_logs(
    session: Session,
    *,
    user: User,
    product: Product,
    sku: ProductSku,
    order: Order,
) -> int:
    existing_log_count = session.scalar(
        select(func.count()).select_from(UserBehaviorLog).where(UserBehaviorLog.user_id == user.id)
    )
    if existing_log_count:
        return int(existing_log_count)

    session.add_all(
        [
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="search",
                target_type="search",
                ext_json={
                    "query": "明制",
                    "result_count": 1,
                    "sort": "default",
                },
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="search",
                target_type="semantic_search",
                ext_json={
                    "query": "适合春日出游的刺绣汉服",
                    "mode": "semantic",
                    "result_count": 3,
                },
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="view_product",
                target_id=product.id,
                target_type="product",
                ext_json={"source": "seed_demo_data"},
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="add_to_cart",
                target_id=product.id,
                target_type="product",
                ext_json={"sku_id": sku.id, "quantity": 2},
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="create_order",
                target_id=order.id,
                target_type="order",
                ext_json={
                    "order_no": order.order_no,
                    "item_count": len(order.items),
                    "payable_amount": str(order.payable_amount),
                    "product_ids": [item.product_id for item in order.items],
                },
            ),
            UserBehaviorLog(
                user_id=user.id,
                behavior_type="pay_order",
                target_id=order.id,
                target_type="order",
                ext_json={
                    "order_no": order.order_no,
                    "payment_method": "alipay",
                    "payable_amount": str(order.payable_amount),
                    "product_ids": [item.product_id for item in order.items],
                },
            ),
        ]
    )
    session.flush()
    return 6


def seed_demo_data(session: Session) -> dict[str, object]:
    base_result = seed_base_data(session)
    user, address = ensure_demo_user(session)
    paid_order, paid_product, paid_sku = ensure_demo_order(
        session,
        user=user,
        address=address,
        product_name=DEMO_PAID_PRODUCT_NAME,
        quantity=2,
        idempotency_key=DEMO_PAID_ORDER_KEY,
        status="PAID",
        buyer_note="演示用户已完成支付的样例订单",
        payment_method="alipay",
    )
    ensure_demo_order(
        session,
        user=user,
        address=address,
        product_name=DEMO_PENDING_PRODUCT_NAME,
        quantity=1,
        idempotency_key=DEMO_PENDING_ORDER_KEY,
        status="PENDING_PAYMENT",
        buyer_note="演示用户待支付的样例订单",
    )
    ensure_demo_behavior_logs(
        session,
        user=user,
        product=paid_product,
        sku=paid_sku,
        order=paid_order,
    )

    session.commit()

    interest_profile = build_user_interest_profile(session, user_id=user.id)
    point_account = session.scalar(
        select(PointAccount)
        .options(selectinload(PointAccount.member_level))
        .where(PointAccount.user_id == user.id)
    )
    if point_account is None or point_account.member_level is None:
        raise RuntimeError("demo user point account missing after seed")

    demo_order_count = session.scalar(
        select(func.count()).select_from(Order).where(Order.user_id == user.id)
    )

    return {
        "admin_users": base_result["admin_users"],
        "products": base_result["products"],
        "demo_user_email": user.email,
        "demo_orders": int(demo_order_count or 0),
        "behavior_logs": interest_profile.behavior_count,
        "points_balance": point_account.points_balance,
        "member_level": point_account.member_level.code,
    }


def main() -> None:
    session = get_session_factory()()
    try:
        result = seed_demo_data(session)
        print(
            "Seeded demo data"
            f" demo_user={result['demo_user_email']}"
            f" demo_orders={result['demo_orders']}"
            f" behavior_logs={result['behavior_logs']}"
            f" points_balance={result['points_balance']}"
            f" member_level={result['member_level']}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
