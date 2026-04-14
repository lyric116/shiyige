from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.v1.admin_auth import get_current_admin
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.models.order import Order
from backend.app.models.product import Product
from backend.app.models.user import User


router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users_total = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    products_total = db.scalar(select(func.count()).select_from(Product)) or 0
    orders_total = db.scalar(select(func.count()).select_from(Order)) or 0
    paid_orders = db.scalar(select(func.count()).select_from(Order).where(Order.status == "PAID")) or 0
    pending_orders = (
        db.scalar(select(func.count()).select_from(Order).where(Order.status == "PENDING_PAYMENT")) or 0
    )

    return build_response(
        request=request,
        code=0,
        message="ok",
        data={
            "users_total": users_total,
            "active_users": active_users,
            "products_total": products_total,
            "orders_total": orders_total,
            "paid_orders": paid_orders,
            "pending_orders": pending_orders,
        },
        status_code=200,
    )
