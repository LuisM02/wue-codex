"""Complete cost estimation and immutable quotation endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.furniture_plan import FurniturePlan
from app.models.quotation import Quotation
from app.schemas.quotations import CompleteCostRead, CostSelection, QuotationRead
from app.services import cost_selection, plans, quotations
from app.services.complete_cost import CompleteCost

plans_router = APIRouter(prefix="/plans", tags=["quotations"])
quotations_router = APIRouter(prefix="/quotations", tags=["quotations"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


def require_plan(session: Session, plan_id: UUID) -> FurniturePlan:
    plan = plans.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


def require_quotation(session: Session, quotation_id: UUID) -> Quotation:
    quotation = quotations.get_quotation(session, quotation_id)
    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found",
        )
    return quotation


def calculate(
    session: Session,
    plan: FurniturePlan,
    selection: CostSelection,
) -> CompleteCost:
    try:
        return cost_selection.calculate_selected_complete_cost(
            session,
            plan,
            **selection.model_dump(),
        )
    except cost_selection.SelectedCostResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except cost_selection.CALCULATION_STATE_ERRORS as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@plans_router.get("/{plan_id}/complete-cost", response_model=CompleteCostRead)
def get_complete_cost(
    plan_id: UUID,
    material_id: Annotated[UUID, Query()],
    hardware_material_id: Annotated[UUID, Query()],
    labor_rate_id: Annotated[UUID, Query()],
    session: SessionDependency,
) -> CompleteCost:
    return calculate(
        session,
        require_plan(session, plan_id),
        CostSelection(
            material_id=material_id,
            hardware_material_id=hardware_material_id,
            labor_rate_id=labor_rate_id,
        ),
    )


@plans_router.post(
    "/{plan_id}/quotations",
    response_model=QuotationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quotation(
    plan_id: UUID,
    payload: CostSelection,
    session: SessionDependency,
) -> QuotationRead:
    plan = require_plan(session, plan_id)
    estimate = calculate(session, plan, payload)
    return quotations.create_quotation(session, plan, estimate)


@plans_router.get("/{plan_id}/quotations", response_model=list[QuotationRead])
def list_quotations(
    plan_id: UUID,
    session: SessionDependency,
) -> list[QuotationRead]:
    require_plan(session, plan_id)
    return quotations.list_plan_quotations(session, plan_id)


@quotations_router.get("/{quotation_id}", response_model=QuotationRead)
def get_quotation(
    quotation_id: UUID,
    session: SessionDependency,
) -> QuotationRead:
    return require_quotation(session, quotation_id)


@quotations_router.delete(
    "/{quotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_quotation(
    quotation_id: UUID,
    session: SessionDependency,
) -> Response:
    quotations.delete_quotation(
        session,
        require_quotation(session, quotation_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
