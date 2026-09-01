"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes.classification import router as classification_router
from app.api.routes.dimensions import router as dimensions_router
from app.api.routes.furniture import furniture_router, project_furniture_router
from app.api.routes.furniture_images import router as furniture_images_router
from app.api.routes.health import router as health_router
from app.api.routes.material_cost import router as material_cost_router
from app.api.routes.materials import materials_router, prices_router
from app.api.routes.plans import furniture_plans_router, plans_router
from app.api.routes.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(projects_router)
api_router.include_router(project_furniture_router)
api_router.include_router(furniture_images_router)
api_router.include_router(classification_router)
api_router.include_router(dimensions_router)
api_router.include_router(materials_router)
api_router.include_router(prices_router)
api_router.include_router(material_cost_router)
api_router.include_router(furniture_plans_router)
api_router.include_router(plans_router)
api_router.include_router(furniture_router)
