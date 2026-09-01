"""Read-only finalized-plan hardware cost endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.hardware_cost import HardwareCostRead
from app.services import hardware_cost as cost_service
from app.services import hardware_quantity as quantity_service
from app.services import materials as material_service
from app.services import plans as plan_service

router = APIRouter(prefix="/plans", tags=["hardware-cost"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


@router.get("/{plan_id}/hardware-cost", response_model=HardwareCostRead)
def get_hardware_cost(
    plan_id: UUID,
    material_id: Annotated[UUID, Query()],
    session: SessionDependency,
) -> HardwareCostRead:
    plan = plan_service.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    material = material_service.get_material(session, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    price = material_service.get_latest_price(session, material.id)
    try:
        return cost_service.calculate_hardware_cost(plan, material, price)
    except (
        cost_service.HardwareMaterialRequiredError,
        cost_service.ActiveHardwareRequiredError,
        cost_service.PieceUnitRequiredError,
        cost_service.WoodScrewNameRequiredError,
        cost_service.HardwarePriceRequiredError,
        cost_service.HardwarePriceMismatchError,
        quantity_service.PlanNotFinalizedError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
