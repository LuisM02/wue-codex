"""Pure Decimal labor cost tests."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, PlanStatus
from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.services.labor_cost import (
    ActiveLaborRateRequiredError,
    LaborRatePriceMismatchError,
    LaborRatePriceRequiredError,
    calculate_labor_cost,
)
from app.services.labor_quantity import PlanNotFinalizedError


@dataclass(frozen=True)
class Component:
    component_name: str
    component_type: ComponentType


@dataclass(frozen=True)
class Plan:
    id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    status: PlanStatus
    components: list[Component]


def chair_plan(*, status: PlanStatus = PlanStatus.FINALIZED) -> Plan:
    return Plan(
        id=uuid4(),
        furniture_id=uuid4(),
        revision=2,
        furniture_type=FurnitureType.CHAIR,
        status=status,
        components=[
            Component("seat", ComponentType.PANEL),
            Component("backrest", ComponentType.PANEL),
            *(Component(f"leg_{index}", ComponentType.LEG) for index in range(4)),
        ],
    )


def labor_rate(*, is_active: bool = True) -> LaborRate:
    return LaborRate(
        id=uuid4(),
        rate_name="Standard woodworking",
        is_active=is_active,
    )


def price(
    selected: LaborRate,
    value: str = "123.456789",
    *,
    labor_rate_id: UUID | None = None,
) -> LaborRatePrice:
    return LaborRatePrice(
        id=uuid4(),
        labor_rate_id=labor_rate_id or selected.id,
        rate_per_hour=Decimal(value),
        effective_date=date(2099, 1, 1),
    )


def test_calculates_exact_cost_from_live_labor_hours() -> None:
    source = chair_plan()
    selected = labor_rate()
    selected_price = price(selected)

    result = calculate_labor_cost(source, selected, selected_price)

    assert result.labor_hours == Decimal("2.50")
    assert result.rate_per_hour == Decimal("123.456789")
    assert result.total_cost == Decimal("308.64197250")
    assert result.price_id == selected_price.id
    assert len(result.rules) == 3


def test_requires_price_active_rate_and_matching_history() -> None:
    source = chair_plan()
    selected = labor_rate()

    with pytest.raises(LaborRatePriceRequiredError, match="no price history"):
        calculate_labor_cost(source, selected, None)

    inactive = labor_rate(is_active=False)
    with pytest.raises(ActiveLaborRateRequiredError, match="active"):
        calculate_labor_cost(source, inactive, price(inactive))

    with pytest.raises(LaborRatePriceMismatchError, match="does not match"):
        calculate_labor_cost(
            source,
            selected,
            price(selected, labor_rate_id=uuid4()),
        )


def test_draft_plan_is_not_a_costing_source() -> None:
    source = chair_plan(status=PlanStatus.DRAFT)
    selected = labor_rate()

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_labor_cost(source, selected, price(selected))
