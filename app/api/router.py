from fastapi import APIRouter

from app.api.routes import accounting, ai, auth, inventory, master, purchasing, sales

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(master.router)
api_router.include_router(sales.router)
api_router.include_router(purchasing.router)
api_router.include_router(inventory.router)
api_router.include_router(accounting.router)
api_router.include_router(ai.router)
