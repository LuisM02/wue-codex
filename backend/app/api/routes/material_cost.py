"""Read-only finalized-plan material cost endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.material_cost import MaterialCostRead
from app.services import material_cost as cost_service
from app.services import materials as material_service
from app.services import plans as plan_service
from app.services import reconstruction_3d as reconstruction_service

router = APIRouter(prefix="/plans", tags=["material-cost"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


@router.get("/{plan_id}/material-cost", response_model=MaterialCostRead)
def get_material_cost(
    plan_id: UUID,
    material_id: Annotated[UUID, Query()],
    session: SessionDependency,
) -> MaterialCostRead:
    plan = plan_service.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    material = material_service.get_material(session, material_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")
    price = material_service.get_latest_price(session, material.id)
    try:
        return cost_service.calculate_material_cost(plan, material, price)
    except (
        cost_service.WoodMaterialRequiredError,
        cost_service.ActiveMaterialRequiredError,
        cost_service.MaterialPriceRequiredError,
        cost_service.MaterialPriceUnitMismatchError,
        cost_service.UnsupportedVolumeUnitError,
        reconstruction_service.PlanNotFinalizedError,
        reconstruction_service.ComponentDepthRequiredError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
