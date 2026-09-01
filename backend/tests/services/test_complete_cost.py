"""Pure complete-cost composition tests."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, MaterialType, MaterialUnit, PlanStatus
from app.models.labor_rate import LaborRate
from app.models.labor_rate_price import LaborRatePrice
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.services.complete_cost import calculate_complete_cost
from app.services.reconstruction_3d import PlanNotFinalizedError


@dataclass(frozen=True)
class Component:
    id: UUID
    component_name: str
    component_type: ComponentType
    width: Decimal
    height: Decimal
    depth: Decimal
    thickness: None = None
    x: Decimal = Decimal("0")
    y: Decimal = Decimal("0")
    z: Decimal = Decimal("0")
    rotation: Decimal = Decimal("0")
    quantity: int = 1
    sort_order: int = 0


@dataclass(frozen=True)
class Plan:
    id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    status: PlanStatus
    components: list[Component]


def chair_plan(*, status: PlanStatus = PlanStatus.FINALIZED) -> Plan:
    names = (
        ("seat", ComponentType.PANEL, Decimal("10")),
        ("backrest", ComponentType.PANEL, Decimal("10")),
        *(
            (f"leg_{index}", ComponentType.LEG, Decimal("1"))
            for index in range(4)
        ),
    )
    return Plan(
        id=uuid4(),
        furniture_id=uuid4(),
        revision=1,
        furniture_type=FurnitureType.CHAIR,
        status=status,
        components=[
            Component(
                id=uuid4(),
                component_name=name,
                component_type=component_type,
                width=size,
                height=size,
                depth=size,
                sort_order=index,
            )
            for index, (name, component_type, size) in enumerate(names)
        ],
    )


def material(
    name: str,
    material_type: MaterialType,
    unit: MaterialUnit,
) -> Material:
    return Material(
        id=uuid4(),
        material_name=name,
        material_type=material_type,
        unit=unit,
        is_active=True,
    )


def material_price(selected: Material, value: str) -> MaterialPrice:
    return MaterialPrice(
        id=uuid4(),
        material_id=selected.id,
        price_per_unit=Decimal(value),
        unit=selected.unit,
        effective_date=date(2099, 1, 1),
    )


def labor_selection() -> tuple[LaborRate, LaborRatePrice]:
    labor_rate = LaborRate(
        id=uuid4(),
        rate_name="Standard woodworking",
        is_active=True,
    )
    return labor_rate, LaborRatePrice(
        id=uuid4(),
        labor_rate_id=labor_rate.id,
        rate_per_hour=Decimal("100"),
        effective_date=date(2099, 1, 1),
    )


def test_total_is_exact_sum_of_three_cost_domains() -> None:
    source = chair_plan()
    wood = material("Oak", MaterialType.WOOD, MaterialUnit.CUBIC_MILLIMETER)
    screw = material("Wood screw", MaterialType.HARDWARE, MaterialUnit.PIECE)
    labor_rate, labor_price = labor_selection()

    result = calculate_complete_cost(
        source,  # type: ignore[arg-type]
        wood,
        material_price(wood, "0.1"),
        screw,
        material_price(screw, "2"),
        labor_rate,
        labor_price,
    )

    assert result.material.total_volume_mm3 == Decimal("2004")
    assert result.material.total_cost == Decimal("200.4")
    assert result.hardware.quantity == 10
    assert result.hardware.total_cost == Decimal("20")
    assert result.labor.labor_hours == Decimal("2.50")
    assert result.labor.total_cost == Decimal("250.00")
    assert result.total_cost == Decimal("470.40")
    assert result.total_cost == (
        result.material.total_cost
        + result.hardware.total_cost
        + result.labor.total_cost
    )


def test_complete_cost_is_repeatable_and_rejects_draft() -> None:
    source = chair_plan()
    wood = material("Oak", MaterialType.WOOD, MaterialUnit.CUBIC_MILLIMETER)
    screw = material("Wood screw", MaterialType.HARDWARE, MaterialUnit.PIECE)
    wood_price = material_price(wood, "0.1")
    screw_price = material_price(screw, "2")
    labor_rate, labor_price = labor_selection()

    first = calculate_complete_cost(
        source,  # type: ignore[arg-type]
        wood,
        wood_price,
        screw,
        screw_price,
        labor_rate,
        labor_price,
    )
    second = calculate_complete_cost(
        source,  # type: ignore[arg-type]
        wood,
        wood_price,
        screw,
        screw_price,
        labor_rate,
        labor_price,
    )
    assert first == second

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_complete_cost(
            chair_plan(status=PlanStatus.DRAFT),  # type: ignore[arg-type]
            wood,
            wood_price,
            screw,
            screw_price,
            labor_rate,
            labor_price,
        )
