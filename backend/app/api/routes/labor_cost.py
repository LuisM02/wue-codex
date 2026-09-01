"""Read-only finalized-plan labor cost endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.labor_cost import LaborCostRead
from app.services import labor_cost as cost_service
from app.services import labor_quantity as quantity_service
from app.services import labor_rates as labor_rate_service
from app.services import plans as plan_service

router = APIRouter(prefix="/plans", tags=["labor-cost"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


@router.get("/{plan_id}/labor-cost", response_model=LaborCostRead)
def get_labor_cost(
    plan_id: UUID,
    labor_rate_id: Annotated[UUID, Query()],
    session: SessionDependency,
) -> LaborCostRead:
    plan = plan_service.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    labor_rate = labor_rate_service.get_labor_rate(session, labor_rate_id)
    if labor_rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labor rate not found",
        )
    price = labor_rate_service.get_latest_price(session, labor_rate.id)
    try:
        return cost_service.calculate_labor_cost(plan, labor_rate, price)
    except (
        cost_service.ActiveLaborRateRequiredError,
        cost_service.LaborRatePriceRequiredError,
        cost_service.LaborRatePriceMismatchError,
        quantity_service.PlanNotFinalizedError,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
