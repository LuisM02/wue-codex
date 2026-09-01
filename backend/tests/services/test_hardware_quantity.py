"""Pure WUE v1 wood-screw quantity rule tests."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, PlanStatus
from app.services.hardware_quantity import (
    HardwareQuantity,
    PlanNotFinalizedError,
    calculate_hardware_quantity,
)


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


def component(
    name: str,
    component_type: ComponentType = ComponentType.PANEL,
    *,
    quantity: int = 1,
) -> Component:
    return Component(name, component_type, quantity)


def plan(
    furniture_type: FurnitureType,
    *components: Component,
    status: PlanStatus = PlanStatus.FINALIZED,
) -> Plan:
    return Plan(
        id=uuid4(),
        furniture_id=uuid4(),
        revision=2,
        furniture_type=furniture_type,
        status=status,
        components=list(components),
    )


def connection_summary(result: HardwareQuantity) -> list[tuple[str, int, int]]:
    return [
        (item.connection_type.value, item.connection_count, item.screw_quantity)
        for item in result.connections
    ]


def test_default_chair_has_ten_wood_screws() -> None:
    source = plan(
        FurnitureType.CHAIR,
        component("seat"),
        component("backrest"),
        *(component(f"leg_{index}", ComponentType.LEG) for index in range(4)),
    )

    result = calculate_hardware_quantity(source)

    assert connection_summary(result) == [
        ("leg_connections", 4, 8),
        ("backrest_connections", 1, 2),
    ]
    assert result.total_connections == 5
    assert result.total_quantity == 10


def test_default_dining_table_has_eight_wood_screws() -> None:
    source = plan(
        FurnitureType.DINING_TABLE,
        component("tabletop"),
        *(component(f"leg_{index}", ComponentType.LEG) for index in range(4)),
    )

    result = calculate_hardware_quantity(source)

    assert connection_summary(result) == [("leg_connections", 4, 8)]
    assert result.total_quantity == 8


def test_default_bookshelf_has_twenty_screws_and_excludes_back_panel() -> None:
    source = plan(
        FurnitureType.BOOKSHELF,
        component("left_side"),
        component("right_side"),
        component("top_panel"),
        component("bottom_panel"),
        component("back_panel", quantity=20),
        component("shelf_1"),
        component("shelf_2"),
        component("shelf_3"),
    )

    result = calculate_hardware_quantity(source)

    assert connection_summary(result) == [
        ("carcass_connections", 4, 8),
        ("shelf_connections", 6, 12),
    ]
    assert result.total_connections == 10
    assert result.total_quantity == 20


def test_counts_component_quantity_and_only_valid_ascii_shelf_names() -> None:
    source = plan(
        FurnitureType.BOOKSHELF,
        component("left_side", quantity=2),
        component("right_side"),
        component("top_panel"),
        component("bottom_panel", quantity=2),
        component("shelf_10", quantity=3),
        component("shelf_01", quantity=50),
        component("shelf_١", quantity=50),
    )

    result = calculate_hardware_quantity(source)

    assert connection_summary(result) == [
        ("carcass_connections", 9, 18),
        ("shelf_connections", 9, 18),
    ]
    assert result.total_quantity == 36


def test_metadata_identifies_the_documented_v1_rule() -> None:
    result = calculate_hardware_quantity(
        plan(FurnitureType.DINING_TABLE, component("leg", ComponentType.LEG))
    )

    assert result.item_code == "wood_screw"
    assert result.item_name == "Wood screw"
    assert result.category == "hardware"
    assert result.unit == "piece"
    assert result.rule_name == "WUE v1 wood-screw connection rule"
    assert result.screws_per_connection == 2


def test_draft_plan_is_rejected() -> None:
    source = plan(
        FurnitureType.CHAIR,
        component("leg", ComponentType.LEG),
        status=PlanStatus.DRAFT,
    )

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_hardware_quantity(source)
