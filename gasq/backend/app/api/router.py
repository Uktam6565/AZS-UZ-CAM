from fastapi import APIRouter

from app.api.queue import router as queue_router
from app.api.driver import router as driver_router
from app.api.stations import router as stations_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.routes.notifications import router as notifications_router  # ← ВАЖНО: notifications

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(stations_router, prefix="/stations")

# ✅ ВАЖНО: БЕЗ prefix="/queue"
api_router.include_router(queue_router)

# 🚗 очередь водителей (по claim_code)
api_router.include_router(driver_router)

api_router.include_router(users_router)  # users_router уже с prefix="/admin/users"

api_router.include_router(notifications_router)