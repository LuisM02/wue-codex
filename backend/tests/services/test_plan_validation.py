"""Pure exact semantic finalization tests."""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.core.enums import ComponentType, FurnitureType
from app.services.plan_geometry import generate_default_components
from app.services.plan_validation import (
    PlanSemanticValidationError,
    validate_plan_components,
)


@dataclass(frozen=True)
class Identity:
    component_name: str
    component_type: ComponentType


def panel(name: str) -> Identity:
    return Identity(name, ComponentType.PANEL)


def leg(name: str = "leg") -> Identity:
    return Identity(name, ComponentType.LEG)


@pytest.mark.parametrize("furniture_type", list(FurnitureType))
def test_all_generated_defaults_are_semantically_valid(
    furniture_type: FurnitureType,
) -> None:
    defaults = generate_default_components(
        furniture_type,
        width_mm=Decimal("1000"),
        height_mm=Decimal("1200"),
        depth_mm=Decimal("600"),
    )

    validate_plan_components(furniture_type, defaults)


def test_chair_accepts_any_leg_identity_but_exact_seat_and_backrest() -> None:
    validate_plan_components(
        FurnitureType.CHAIR,
        [panel("seat"), panel("backrest"), leg("custom_support")],
    )


def test_chair_reports_cardinality_and_unrecognized_panels() -> None:
    components = [
        panel("seat"),
        panel("seat"),
        panel("Backrest"),
        panel("armrest"),
    ]

    with pytest.raises(PlanSemanticValidationError) as exc_info:
        validate_plan_components(FurnitureType.CHAIR, components)

    assert exc_info.value.issues == (
        "chair requires at least one leg",
        "chair requires exactly one seat panel (found 2)",
        "chair requires exactly one backrest panel (found 0)",
        "unrecognized chair components: Backrest:panel, armrest:panel",
    )


def test_dining_table_requires_legs_and_exactly_one_tabletop() -> None:
    valid = [panel("tabletop"), leg("center_leg")]
    validate_plan_components(FurnitureType.DINING_TABLE, valid)

    invalid = [panel("tabletop"), panel("tabletop"), panel("apron")]
    with pytest.raises(PlanSemanticValidationError) as exc_info:
        validate_plan_components(FurnitureType.DINING_TABLE, invalid)

    assert exc_info.value.issues == (
        "dining_table requires at least one leg",
        "dining_table requires exactly one tabletop panel (found 2)",
        "unrecognized dining_table components: apron:panel",
    )


def required_bookshelf() -> list[Identity]:
    return [
        panel("left_side"),
        panel("right_side"),
        panel("top_panel"),
        panel("bottom_panel"),
        panel("back_panel"),
    ]


@pytest.mark.parametrize("shelf_name", ["shelf_1", "shelf_9", "shelf_10", "shelf_999"])
def test_bookshelf_accepts_exact_positive_shelf_identifiers(shelf_name: str) -> None:
    validate_plan_components(
        FurnitureType.BOOKSHELF,
        [*required_bookshelf(), panel(shelf_name)],
    )


@pytest.mark.parametrize(
    "shelf_name",
    ["shelf_0", "shelf_01", "shelf_x", "Shelf_1", "shelf_1٢"],
)
def test_bookshelf_rejects_invalid_shelf_identifiers(shelf_name: str) -> None:
    with pytest.raises(PlanSemanticValidationError) as exc_info:
        validate_plan_components(
            FurnitureType.BOOKSHELF,
            [*required_bookshelf(), panel(shelf_name)],
        )

    assert exc_info.value.issues == (
        "bookshelf requires at least one valid shelf_N panel",
        f"unrecognized bookshelf components: {shelf_name}:panel",
    )


def test_bookshelf_rejects_duplicate_required_and_shelf_identities() -> None:
    components = [
        *required_bookshelf(),
        panel("left_side"),
        panel("shelf_2"),
        panel("shelf_1"),
        panel("shelf_2"),
        leg("support"),
    ]

    with pytest.raises(PlanSemanticValidationError) as exc_info:
        validate_plan_components(FurnitureType.BOOKSHELF, components)

    assert exc_info.value.issues == (
        "bookshelf requires exactly one left_side panel (found 2)",
        "bookshelf shelf identities must be unique: shelf_2",
        "unrecognized bookshelf components: support:leg",
    )


def test_bookshelf_reports_all_missing_required_panels_in_fixed_order() -> None:
    with pytest.raises(PlanSemanticValidationError) as exc_info:
        validate_plan_components(FurnitureType.BOOKSHELF, [panel("shelf_1")])

    assert exc_info.value.issues == (
        "bookshelf requires exactly one left_side panel (found 0)",
        "bookshelf requires exactly one right_side panel (found 0)",
        "bookshelf requires exactly one top_panel panel (found 0)",
        "bookshelf requires exactly one bottom_panel panel (found 0)",
        "bookshelf requires exactly one back_panel panel (found 0)",
    )
