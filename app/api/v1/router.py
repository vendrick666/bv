"""
Главный роутер API v1
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.items import router as items_router
from app.api.v1.endpoints.categories import router as categories_router
from app.api.v1.endpoints.cart import router as cart_router
from app.api.v1.endpoints.orders import router as orders_router
from app.api.v1.endpoints.websocket import router as ws_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.support import router as support_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.upload import router as upload_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(items_router)
api_router.include_router(categories_router)
api_router.include_router(cart_router)
api_router.include_router(orders_router)
api_router.include_router(ws_router)
api_router.include_router(reports_router)
api_router.include_router(admin_router)
api_router.include_router(support_router)
api_router.include_router(users_router)
api_router.include_router(upload_router)
