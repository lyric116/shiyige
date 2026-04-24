from fastapi import APIRouter

from backend.app.api.v1.admin_auth import router as admin_auth_router
from backend.app.api.v1.admin_dashboard import router as admin_dashboard_router
from backend.app.api.v1.admin_media import router as admin_media_router
from backend.app.api.v1.admin_orders import router as admin_orders_router
from backend.app.api.v1.admin_products import router as admin_products_router
from backend.app.api.v1.admin_recommendations import router as admin_recommendations_router
from backend.app.api.v1.admin_reindex import router as admin_reindex_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.cart import router as cart_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.media import router as media_router
from backend.app.api.v1.member import router as member_router
from backend.app.api.v1.orders import router as orders_router
from backend.app.api.v1.products import router as products_router
from backend.app.api.v1.reviews import router as reviews_router
from backend.app.api.v1.search import router as search_router
from backend.app.api.v1.users import router as users_router

router = APIRouter(prefix="/api/v1")
router.include_router(admin_dashboard_router)
router.include_router(admin_auth_router)
router.include_router(admin_media_router)
router.include_router(admin_orders_router)
router.include_router(admin_products_router)
router.include_router(admin_recommendations_router)
router.include_router(admin_reindex_router)
router.include_router(auth_router)
router.include_router(cart_router)
router.include_router(health_router)
router.include_router(member_router)
router.include_router(media_router)
router.include_router(orders_router)
router.include_router(products_router)
router.include_router(reviews_router)
router.include_router(search_router)
router.include_router(users_router)
