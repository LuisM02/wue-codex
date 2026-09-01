"""Parametric 2D plan generation and draft component endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.furniture_plan import FurniturePlan
from app.schemas.hardware_quantity import HardwareQuantityRead
from app.schemas.labor_quantity import LaborQuantityRead
from app.schemas.material_quantity import MaterialQuantityRead
from app.schemas.plans import (
    ComponentCreate,
    ComponentRead,
    ComponentUpdate,
    FurniturePlanRead,
)
from app.schemas.reconstruction_3d import PlanGeometry3DRead
from app.services import dimensions as dimension_service
from app.services import furniture as furniture_service
from app.services import hardware_quantity as hardware_quantity_service
from app.services import labor_quantity as labor_quantity_service
from app.services import material_quantity as quantity_service
from app.services import plans as plan_service
from app.services import reconstruction_3d as reconstruction_service
from app.services.plan_geometry import PlanGeometryRangeError
from app.services.plan_validation import PlanSemanticValidationError

furniture_plans_router = APIRouter(
    prefix="/furniture/{furniture_id}/plans",
    tags=["2d-plans"],
)
plans_router = APIRouter(prefix="/plans", tags=["2d-plans"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


def require_plan(session: Session, plan_id: UUID) -> FurniturePlan:
    plan = plan_service.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@furniture_plans_router.post(
    "",
    response_model=FurniturePlanRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_plan(
    furniture_id: UUID,
    session: SessionDependency,
) -> FurniturePlanRead:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    try:
        return plan_service.create_initial_plan(session, furniture)
    except dimension_service.DimensionsRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except plan_service.DraftPlanExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except plan_service.PlanHistoryExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PlanGeometryRangeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@furniture_plans_router.get("", response_model=list[FurniturePlanRead])
def list_plans(
    furniture_id: UUID,
    session: SessionDependency,
) -> list[FurniturePlanRead]:
    if furniture_service.get_furniture(session, furniture_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    return plan_service.list_furniture_plans(session, furniture_id)


@plans_router.get("/{plan_id}", response_model=FurniturePlanRead)
def get_plan(plan_id: UUID, session: SessionDependency) -> FurniturePlanRead:
    return require_plan(session, plan_id)


@plans_router.get(
    "/{plan_id}/geometry-3d",
    response_model=PlanGeometry3DRead,
)
def get_plan_geometry_3d(
    plan_id: UUID,
    session: SessionDependency,
) -> PlanGeometry3DRead:
    plan = require_plan(session, plan_id)
    try:
        return reconstruction_service.build_plan_geometry(plan)
    except reconstruction_service.PlanNotFinalizedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except reconstruction_service.ComponentDepthRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.get(
    "/{plan_id}/material-quantity",
    response_model=MaterialQuantityRead,
)
def get_material_quantity(
    plan_id: UUID,
    session: SessionDependency,
) -> MaterialQuantityRead:
    plan = require_plan(session, plan_id)
    try:
        return quantity_service.calculate_material_quantity(plan)
    except reconstruction_service.PlanNotFinalizedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except reconstruction_service.ComponentDepthRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.get(
    "/{plan_id}/hardware-quantity",
    response_model=HardwareQuantityRead,
)
def get_hardware_quantity(
    plan_id: UUID,
    session: SessionDependency,
) -> HardwareQuantityRead:
    plan = require_plan(session, plan_id)
    try:
        return hardware_quantity_service.calculate_hardware_quantity(plan)
    except hardware_quantity_service.PlanNotFinalizedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.get(
    "/{plan_id}/labor-quantity",
    response_model=LaborQuantityRead,
)
def get_labor_quantity(
    plan_id: UUID,
    session: SessionDependency,
) -> LaborQuantityRead:
    plan = require_plan(session, plan_id)
    try:
        return labor_quantity_service.calculate_labor_quantity(plan)
    except labor_quantity_service.PlanNotFinalizedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.post("/{plan_id}/finalize", response_model=FurniturePlanRead)
def finalize_plan(
    plan_id: UUID,
    session: SessionDependency,
) -> FurniturePlanRead:
    plan = require_plan(session, plan_id)
    try:
        return plan_service.finalize_plan(session, plan)
    except plan_service.PlanNotDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PlanSemanticValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.post(
    "/{plan_id}/revisions",
    response_model=FurniturePlanRead,
    status_code=status.HTTP_201_CREATED,
)
def create_revision(
    plan_id: UUID,
    session: SessionDependency,
) -> FurniturePlanRead:
    plan = require_plan(session, plan_id)
    try:
        return plan_service.create_revision(session, plan)
    except plan_service.PlanRevisionSourceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except plan_service.DraftPlanExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.post(
    "/{plan_id}/components",
    response_model=ComponentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_component(
    plan_id: UUID,
    payload: ComponentCreate,
    session: SessionDependency,
) -> ComponentRead:
    plan = require_plan(session, plan_id)
    try:
        return plan_service.add_component(session, plan, payload)
    except plan_service.PlanNotDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.patch(
    "/{plan_id}/components/{component_id}",
    response_model=ComponentRead,
)
def update_component(
    plan_id: UUID,
    component_id: UUID,
    payload: ComponentUpdate,
    session: SessionDependency,
) -> ComponentRead:
    plan = require_plan(session, plan_id)
    component = plan_service.get_component(session, plan_id, component_id)
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    try:
        return plan_service.update_component(session, plan, component, payload)
    except plan_service.PlanNotDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.delete(
    "/{plan_id}/components/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_component(
    plan_id: UUID,
    component_id: UUID,
    session: SessionDependency,
) -> Response:
    plan = require_plan(session, plan_id)
    component = plan_service.get_component(session, plan_id, component_id)
    if component is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    try:
        plan_service.delete_component(session, plan, component)
    except plan_service.PlanNotDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
