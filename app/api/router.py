from fastapi import APIRouter

from app.api.v1 import admin, auth, categories, currency, dashboard, debts, operations, plans, preferences, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(operations.router)
api_router.include_router(currency.router)
api_router.include_router(plans.router)
api_router.include_router(debts.router)
api_router.include_router(dashboard.router)
api_router.include_router(preferences.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
