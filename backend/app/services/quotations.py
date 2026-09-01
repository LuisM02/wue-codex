"""Immutable quotation snapshot persistence."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.furniture_plan import FurniturePlan
from app.models.quotation import Quotation
from app.services._persistence import commit
from app.services.complete_cost import CompleteCost


def create_quotation(
    session: Session,
    plan: FurniturePlan,
    estimate: CompleteCost,
) -> Quotation:
    """Snapshot one fully validated live estimate without overhead."""
    quotation_id = uuid4()
    quotation = Quotation(
        id=quotation_id,
        quotation_number=f"WUE-{quotation_id.hex.upper()}",
        created_at=datetime.now(timezone.utc),
        project_id=plan.furniture.project_id,
        furniture_id=plan.furniture_id,
        plan_id=plan.id,
        plan_revision=plan.revision,
        furniture_type=plan.furniture_type,
        wood_material_id=estimate.material.material_id,
        wood_material_name=estimate.material.material_name,
        wood_price_id=estimate.material.price_id,
        wood_price_per_unit=estimate.material.price_per_unit,
        wood_price_unit=estimate.material.price_unit,
        wood_price_effective_date=estimate.material.price_effective_date,
        wood_quantity=estimate.material.total_quantity_in_price_unit,
        wood_material_cost=estimate.material.total_cost,
        hardware_material_id=estimate.hardware.material_id,
        hardware_material_name=estimate.hardware.material_name,
        hardware_price_id=estimate.hardware.price_id,
        hardware_price_per_piece=estimate.hardware.price_per_piece,
        hardware_price_effective_date=estimate.hardware.price_effective_date,
        hardware_quantity=estimate.hardware.quantity,
        hardware_cost=estimate.hardware.total_cost,
        labor_rate_id=estimate.labor.labor_rate_id,
        labor_rate_name=estimate.labor.labor_rate_name,
        labor_rate_price_id=estimate.labor.price_id,
        labor_rate_per_hour=estimate.labor.rate_per_hour,
        labor_rate_effective_date=estimate.labor.price_effective_date,
        labor_hours=estimate.labor.labor_hours,
        labor_cost=estimate.labor.total_cost,
        total_cost=estimate.total_cost,
    )
    session.add(quotation)
    commit(session)
    session.refresh(quotation)
    return quotation


def list_plan_quotations(session: Session, plan_id: UUID) -> list[Quotation]:
    statement = (
        select(Quotation)
        .where(Quotation.plan_id == plan_id)
        .order_by(Quotation.created_at.desc(), Quotation.id.desc())
    )
    return list(session.scalars(statement).all())


def get_quotation(session: Session, quotation_id: UUID) -> Quotation | None:
    return session.get(Quotation, quotation_id)


def delete_quotation(session: Session, quotation: Quotation) -> None:
    session.delete(quotation)
    commit(session)
