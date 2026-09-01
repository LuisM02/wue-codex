"""Pure Decimal wood-screw cost calculation tests."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, MaterialType, MaterialUnit, PlanStatus
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.services.hardware_cost import (
    ActiveHardwareRequiredError,
    HardwareMaterialRequiredError,
    HardwarePriceMismatchError,
    HardwarePriceRequiredError,
    PieceUnitRequiredError,
    WoodScrewNameRequiredError,
    calculate_hardware_cost,
)
from app.services.hardware_quantity import PlanNotFinalizedError


@dataclass(frozen=True)
class Component:
    component_name: str
    component_type: ComponentType
    quantity: int = 1


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
        revision=4,
        furniture_type=FurnitureType.CHAIR,
        status=status,
        components=[
            Component("seat", ComponentType.PANEL),
            Component("backrest", ComponentType.PANEL),
            *(Component(f"leg_{index}", ComponentType.LEG) for index in range(4)),
        ],
    )


def material(
    *,
    name: str = "Wood screw",
    material_type: MaterialType = MaterialType.HARDWARE,
    unit: MaterialUnit = MaterialUnit.PIECE,
    is_active: bool = True,
) -> Material:
    return Material(
        id=uuid4(),
        material_name=name,
        material_type=material_type,
        unit=unit,
        is_active=is_active,
    )


def price(
    selected: Material,
    value: str = "1.234567",
    *,
    material_id: UUID | None = None,
    unit: MaterialUnit | None = None,
) -> MaterialPrice:
    return MaterialPrice(
        id=uuid4(),
        material_id=material_id or selected.id,
        price_per_unit=Decimal(value),
        unit=unit or selected.unit,
        effective_date=date(2099, 1, 1),
    )


def test_calculates_exact_cost_from_live_screw_quantity() -> None:
    source = chair_plan()
    selected = material()
    selected_price = price(selected)

    result = calculate_hardware_cost(source, selected, selected_price)

    assert result.plan_id == source.id
    assert result.material_id == selected.id
    assert result.price_id == selected_price.id
    assert result.price_per_piece == Decimal("1.234567")
    assert result.price_unit == MaterialUnit.PIECE
    assert result.quantity == 10
    assert result.total_cost == Decimal("12.345670")
    assert [item.screw_quantity for item in result.connections] == [8, 2]


def test_accepts_exact_wood_screw_name_after_strip_and_casefold() -> None:
    source = chair_plan()
    selected = material(name="  WOOD SCREW  ")

    result = calculate_hardware_cost(source, selected, price(selected, "2"))

    assert result.material_name == "  WOOD SCREW  "
    assert result.total_cost == Decimal("20")


def test_requires_price_and_valid_hardware_selection() -> None:
    source = chair_plan()
    selected = material()

    with pytest.raises(HardwarePriceRequiredError, match="no price history"):
        calculate_hardware_cost(source, selected, None)

    inactive = material(is_active=False)
    with pytest.raises(ActiveHardwareRequiredError, match="active"):
        calculate_hardware_cost(source, inactive, price(inactive))

    wood = material(
        material_type=MaterialType.WOOD,
        unit=MaterialUnit.CUBIC_MILLIMETER,
    )
    with pytest.raises(HardwareMaterialRequiredError, match="hardware material"):
        calculate_hardware_cost(source, wood, price(wood))

    wrong_unit = material(unit=MaterialUnit.CUBIC_CENTIMETER)
    with pytest.raises(PieceUnitRequiredError, match="unit piece"):
        calculate_hardware_cost(source, wrong_unit, price(wrong_unit))

    wrong_name = material(name="Machine screw")
    with pytest.raises(WoodScrewNameRequiredError, match="name Wood screw"):
        calculate_hardware_cost(source, wrong_name, price(wrong_name))


@pytest.mark.parametrize(
    "selected_price",
    ["other_material", "other_unit"],
)
def test_requires_price_to_match_selected_hardware(selected_price: str) -> None:
    source = chair_plan()
    selected = material()
    if selected_price == "other_material":
        invalid_price = price(selected, material_id=uuid4())
    else:
        invalid_price = price(selected, unit=MaterialUnit.CUBIC_METER)

    with pytest.raises(HardwarePriceMismatchError, match="does not match"):
        calculate_hardware_cost(source, selected, invalid_price)


def test_draft_plan_is_not_a_costing_source() -> None:
    source = chair_plan(status=PlanStatus.DRAFT)
    selected = material()

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_hardware_cost(source, selected, price(selected))
