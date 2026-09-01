"""Pure Decimal material unit conversion and cost tests."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, MaterialType, MaterialUnit, PlanStatus
from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.services.material_cost import (
    BOARD_FOOT_IN_MM3,
    ActiveMaterialRequiredError,
    MaterialPriceRequiredError,
    MaterialPriceUnitMismatchError,
    UnsupportedVolumeUnitError,
    WoodMaterialRequiredError,
    calculate_material_cost,
    convert_volume_from_mm3,
)
from app.services.reconstruction_3d import PlanNotFinalizedError


@dataclass(frozen=True)
class Component:
    id: UUID
    component_name: str
    component_type: ComponentType
    width: Decimal
    height: Decimal
    depth: Decimal | None
    thickness: Decimal | None
    quantity: int
    sort_order: int
    x: Decimal = Decimal("0")
    y: Decimal = Decimal("0")
    z: Decimal = Decimal("0")
    rotation: Decimal = Decimal("0")


@dataclass(frozen=True)
class Plan:
    id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    status: PlanStatus
    components: tuple[Component, ...]


def component(
    name: str,
    *,
    width: str,
    height: str,
    depth: str,
    quantity: int = 1,
    sort_order: int = 0,
) -> Component:
    return Component(
        id=uuid4(),
        component_name=name,
        component_type=ComponentType.PANEL,
        width=Decimal(width),
        height=Decimal(height),
        depth=Decimal(depth),
        thickness=None,
        quantity=quantity,
        sort_order=sort_order,
    )


def plan(
    *components: Component,
    status: PlanStatus = PlanStatus.FINALIZED,
) -> Plan:
    return Plan(
        id=uuid4(),
        furniture_id=uuid4(),
        revision=1,
        furniture_type=FurnitureType.CHAIR,
        status=status,
        components=components,
    )


def material(
    unit: MaterialUnit,
    *,
    material_type: MaterialType = MaterialType.WOOD,
    is_active: bool = True,
) -> Material:
    return Material(
        id=uuid4(),
        material_name="Oak",
        material_type=material_type,
        unit=unit,
        is_active=is_active,
    )


def price(
    selected: Material,
    value: str = "2",
    *,
    unit: MaterialUnit | None = None,
    material_id: UUID | None = None,
) -> MaterialPrice:
    return MaterialPrice(
        id=uuid4(),
        material_id=material_id or selected.id,
        price_per_unit=Decimal(value),
        unit=unit or selected.unit,
        effective_date=date(2099, 1, 1),
    )


@pytest.mark.parametrize(
    ("volume", "unit", "expected"),
    [
        ("123.456", MaterialUnit.CUBIC_MILLIMETER, "123.456"),
        ("1000", MaterialUnit.CUBIC_CENTIMETER, "1"),
        ("1000000000", MaterialUnit.CUBIC_METER, "1"),
        (str(BOARD_FOOT_IN_MM3), MaterialUnit.BOARD_FOOT, "1"),
    ],
)
def test_converts_canonical_volume_to_every_supported_price_unit(
    volume: str,
    unit: MaterialUnit,
    expected: str,
) -> None:
    assert convert_volume_from_mm3(Decimal(volume), unit) == Decimal(expected)


def test_rejects_piece_as_a_volume_price_unit() -> None:
    with pytest.raises(UnsupportedVolumeUnitError, match="piece"):
        convert_volume_from_mm3(Decimal("1"), MaterialUnit.PIECE)


def test_calculates_transparent_component_and_total_cost() -> None:
    source = plan(
        component("first", width="10", height="10", depth="10", quantity=2),
        component(
            "second",
            width="10",
            height="10",
            depth="20",
            sort_order=1,
        ),
    )
    selected = material(MaterialUnit.CUBIC_CENTIMETER)
    selected_price = price(selected, "2")

    result = calculate_material_cost(
        source,  # type: ignore[arg-type]
        selected,
        selected_price,
    )

    assert result.total_volume_mm3 == Decimal("4000")
    assert result.total_quantity_in_price_unit == Decimal("4")
    assert result.total_cost == Decimal("8")
    assert [item.quantity_in_price_unit for item in result.components] == [
        Decimal("2"),
        Decimal("2"),
    ]
    assert [item.cost for item in result.components] == [Decimal("4"), Decimal("4")]
    assert result.price_id == selected_price.id
    assert result.price_effective_date == date(2099, 1, 1)


def test_board_foot_cost_uses_exact_conversion_constant() -> None:
    source = plan(
        component(
            "board",
            width=str(BOARD_FOOT_IN_MM3),
            height="1",
            depth="1",
        )
    )
    selected = material(MaterialUnit.BOARD_FOOT)

    result = calculate_material_cost(
        source,  # type: ignore[arg-type]
        selected,
        price(selected, "12.5"),
    )

    assert result.total_quantity_in_price_unit == Decimal("1")
    assert result.total_cost == Decimal("12.5")


def test_requires_price_active_wood_and_matching_unit() -> None:
    source = plan(component("panel", width="1", height="1", depth="1"))
    active_wood = material(MaterialUnit.CUBIC_MILLIMETER)

    with pytest.raises(MaterialPriceRequiredError, match="no price history"):
        calculate_material_cost(source, active_wood, None)  # type: ignore[arg-type]
    inactive = material(MaterialUnit.CUBIC_MILLIMETER, is_active=False)
    with pytest.raises(ActiveMaterialRequiredError, match="active"):
        calculate_material_cost(
            source,  # type: ignore[arg-type]
            inactive,
            price(inactive),
        )
    hardware = material(
        MaterialUnit.PIECE,
        material_type=MaterialType.HARDWARE,
    )
    with pytest.raises(WoodMaterialRequiredError, match="wood"):
        calculate_material_cost(
            source,  # type: ignore[arg-type]
            hardware,
            price(hardware),
        )
    with pytest.raises(MaterialPriceUnitMismatchError, match="does not match"):
        calculate_material_cost(
            source,  # type: ignore[arg-type]
            active_wood,
            price(active_wood, unit=MaterialUnit.CUBIC_METER),
        )


def test_draft_plan_is_not_a_costing_source() -> None:
    source = plan(
        component("panel", width="1", height="1", depth="1"),
        status=PlanStatus.DRAFT,
    )
    selected = material(MaterialUnit.CUBIC_MILLIMETER)

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_material_cost(
            source,  # type: ignore[arg-type]
            selected,
            price(selected),
        )
