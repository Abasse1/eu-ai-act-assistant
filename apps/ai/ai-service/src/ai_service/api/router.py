from fastapi import APIRouter

from ai_service.api.routes import assistant, health

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(assistant.router)
