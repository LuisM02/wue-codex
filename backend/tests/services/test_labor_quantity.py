"""Pure WUE v1 labor-hour estimation tests."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, PlanStatus
from app.services.labor_quantity import (
    LABOR_RULE_SET,
    LaborQuantity,
    PlanNotFinalizedError,
    calculate_labor_quantity,
)


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


def component(
    name: str,
    component_type: ComponentType = ComponentType.PANEL,
) -> Component:
    return Component(name, component_type)


def plan(
    furniture_type: FurnitureType,
    *components: Component,
    status: PlanStatus = PlanStatus.FINALIZED,
) -> Plan:
    return Plan(
        id=uuid4(),
        furniture_id=uuid4(),
        revision=3,
        furniture_type=furniture_type,
        status=status,
        components=list(components),
    )


def chair_components() -> tuple[Component, ...]:
    return (
        component("seat"),
        component("backrest"),
        *(component(f"leg_{index}", ComponentType.LEG) for index in range(4)),
    )


def dining_table_components() -> tuple[Component, ...]:
    return (
        component("tabletop"),
        *(component(f"leg_{index}", ComponentType.LEG) for index in range(4)),
    )


def bookshelf_components() -> tuple[Component, ...]:
    return (
        component("left_side"),
        component("right_side"),
        component("top_panel"),
        component("bottom_panel"),
        component("back_panel"),
        component("shelf_1"),
        component("shelf_2"),
        component("shelf_3"),
    )


@pytest.mark.parametrize(
    ("furniture_type", "components", "expected_hours"),
    [
        (FurnitureType.CHAIR, chair_components(), Decimal("2.50")),
        (
            FurnitureType.DINING_TABLE,
            dining_table_components(),
            Decimal("3.20"),
        ),
        (
            FurnitureType.BOOKSHELF,
            bookshelf_components(),
            Decimal("3.35"),
        ),
    ],
)
def test_default_labor_hours(
    furniture_type: FurnitureType,
    components: tuple[Component, ...],
    expected_hours: Decimal,
) -> None:
    result = calculate_labor_quantity(plan(furniture_type, *components))

    assert result.labor_hours == expected_hours
    assert result.labor_hours == sum(
        (item.labor_hours for item in result.rules),
        start=Decimal("0"),
    )


def test_chair_rule_order_and_exact_breakdown() -> None:
    result = calculate_labor_quantity(
        plan(FurnitureType.CHAIR, *chair_components())
    )

    assert [item.rule_code.value for item in result.rules] == [
        "chair_base_assembly",
        "chair_leg_work",
        "chair_backrest_work",
    ]
    assert [
        (item.unit_count, item.hours_per_unit, item.labor_hours)
        for item in result.rules
    ] == [
        (1, Decimal("1.00"), Decimal("1.00")),
        (4, Decimal("0.25"), Decimal("1.00")),
        (1, Decimal("0.50"), Decimal("0.50")),
    ]


def test_dining_table_extra_leg_adds_point_three_hours() -> None:
    result = calculate_labor_quantity(
        plan(
            FurnitureType.DINING_TABLE,
            *dining_table_components(),
            component("extra_leg", ComponentType.LEG),
        )
    )

    assert result.rules[1].unit_count == 5
    assert result.labor_hours == Decimal("3.50")


@pytest.mark.parametrize(
    ("shelf_name", "expected_count"),
    [
        ("shelf_10", 1),
        ("shelf_0", 0),
        ("shelf_01", 0),
        ("shelf_x", 0),
        ("Shelf_1", 0),
        ("shelf_١", 0),
    ],
)
def test_bookshelf_uses_the_exact_ascii_shelf_identity_rule(
    shelf_name: str,
    expected_count: int,
) -> None:
    result = calculate_labor_quantity(
        plan(
            FurnitureType.BOOKSHELF,
            *bookshelf_components()[:5],
            component(shelf_name),
        )
    )

    assert result.rules[2].unit_count == expected_count


def test_result_is_deterministic_read_only_and_self_describing() -> None:
    source = plan(FurnitureType.BOOKSHELF, *bookshelf_components())

    first = calculate_labor_quantity(source)
    second = calculate_labor_quantity(source)

    assert first == second
    assert isinstance(first, LaborQuantity)
    assert first.unit == "hour"
    assert first.rule_set == LABOR_RULE_SET
    assert source.components == list(bookshelf_components())


def test_draft_plan_is_rejected() -> None:
    source = plan(
        FurnitureType.CHAIR,
        *chair_components(),
        status=PlanStatus.DRAFT,
    )

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_labor_quantity(source)
