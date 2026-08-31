"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes.furniture import furniture_router, project_furniture_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(project_furniture_router)
api_router.include_router(furniture_router)
