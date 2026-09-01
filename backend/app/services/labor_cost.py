"""Pure Decimal labor cost calculation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from uuid import UUID

from app.core.enums import FurnitureType
from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.services.labor_quantity import (
    LaborPlan,
    LaborRuleBreakdown,
    calculate_labor_quantity,
)

CALCULATION_PRECISION = 40


class ActiveLaborRateRequiredError(RuntimeError):
    """Raised when a disabled labor rate is selected."""


class LaborRatePriceRequiredError(RuntimeError):
    """Raised when the selected rate has no price history."""


class LaborRatePriceMismatchError(RuntimeError):
    """Raised when a price does not belong to the selected rate."""


@dataclass(frozen=True, slots=True)
class LaborCost:
    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: str
    rule_set: str
    labor_hours: Decimal
    rules: tuple[LaborRuleBreakdown, ...]
    labor_rate_id: UUID
    labor_rate_name: str
    price_id: UUID
    rate_per_hour: Decimal
    price_effective_date: date
    total_cost: Decimal


def calculate_labor_cost(
    plan: LaborPlan,
    labor_rate: LaborRate,
    price: LaborRatePrice | None,
) -> LaborCost:
    """Multiply live approved hours by the latest selected hourly rate."""
    if price is None:
        raise LaborRatePriceRequiredError(
            "Selected labor rate has no price history"
        )
    if not labor_rate.is_active:
        raise ActiveLaborRateRequiredError(
            "Labor cost calculation requires an active labor rate"
        )
    if price.labor_rate_id != labor_rate.id:
        raise LaborRatePriceMismatchError(
            "Latest price does not match the selected labor rate"
        )

    quantity = calculate_labor_quantity(plan)
    with localcontext() as context:
        context.prec = CALCULATION_PRECISION
        total_cost = quantity.labor_hours * price.rate_per_hour
    return LaborCost(
        plan_id=quantity.plan_id,
        furniture_id=quantity.furniture_id,
        revision=quantity.revision,
        furniture_type=quantity.furniture_type,
        unit=quantity.unit,
        rule_set=quantity.rule_set,
        labor_hours=quantity.labor_hours,
        rules=quantity.rules,
        labor_rate_id=labor_rate.id,
        labor_rate_name=labor_rate.rate_name,
        price_id=price.id,
        rate_per_hour=price.rate_per_hour,
        price_effective_date=price.effective_date,
        total_cost=total_cost,
    )
