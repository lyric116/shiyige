from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.v1.admin_auth import get_current_admin
from backend.app.api.v1.orders import serialize_order
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import ProductSku
from backend.app.models.user import User


router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


def build_admin_order_query():
    return (
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.sku).selectinload(ProductSku.inventory),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payment_records),
        )
        .order_by(Order.created_at.desc(), Order.id.desc())
    )


def serialize_admin_order(order: Order) -> dict[str, object]:
    payload = serialize_order(order)
    payload["user"] = {
        "id": order.user.id,
        "email": order.user.email,
        "username": order.user.username,
    }
    return payload


@router.get("")
def list_orders(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_value: str | None = Query(default=None, alias="status"),
    order_no: str | None = None,
    user_id: int | None = None,
):
    query = build_admin_order_query()

    if status_value:
        query = query.where(Order.status == status_value.strip())

    if order_no:
        query = query.where(Order.order_no == order_no.strip())

    if user_id is not None:
        query = query.where(Order.user_id == user_id)

    orders = db.scalars(query).unique().all()
    total = len(orders)
    start = (page - 1) * page_size
    end = start + page_size

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "items": [serialize_admin_order(order) for order in orders[start:end]],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        status_code=200,
    )


@router.get("/{order_id}")
def get_order_detail(
    order_id: int,
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    order = db.scalar(build_admin_order_query().where(Order.id == order_id))
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"order": serialize_admin_order(order)},
        status_code=200,
    )
