"""Pure deterministic default-plan geometry tests."""

from decimal import Decimal

import pytest

from app.core.enums import ComponentType, FurnitureType
from app.services.plan_geometry import (
    PlanGeometryRangeError,
    generate_default_components,
)

OVERALL_WIDTH = Decimal("1000.0000")
OVERALL_HEIGHT = Decimal("1200.0000")
OVERALL_DEPTH = Decimal("600.0000")

EXPECTED_COMPONENTS = {
    FurnitureType.CHAIR: (
        ("seat", ComponentType.PANEL),
        ("backrest", ComponentType.PANEL),
        ("front_left_leg", ComponentType.LEG),
        ("front_right_leg", ComponentType.LEG),
        ("rear_left_leg", ComponentType.LEG),
        ("rear_right_leg", ComponentType.LEG),
    ),
    FurnitureType.DINING_TABLE: (
        ("tabletop", ComponentType.PANEL),
        ("front_left_leg", ComponentType.LEG),
        ("front_right_leg", ComponentType.LEG),
        ("rear_left_leg", ComponentType.LEG),
        ("rear_right_leg", ComponentType.LEG),
    ),
    FurnitureType.BOOKSHELF: (
        ("left_side", ComponentType.PANEL),
        ("right_side", ComponentType.PANEL),
        ("top_panel", ComponentType.PANEL),
        ("bottom_panel", ComponentType.PANEL),
        ("back_panel", ComponentType.PANEL),
        ("shelf_1", ComponentType.PANEL),
        ("shelf_2", ComponentType.PANEL),
        ("shelf_3", ComponentType.PANEL),
    ),
}


@pytest.mark.parametrize("furniture_type", list(FurnitureType))
def test_generates_exact_ordered_defaults_inside_overall_bounds(
    furniture_type: FurnitureType,
) -> None:
    components = generate_default_components(
        furniture_type,
        width_mm=OVERALL_WIDTH,
        height_mm=OVERALL_HEIGHT,
        depth_mm=OVERALL_DEPTH,
    )

    assert tuple(
        (component.component_name, component.component_type)
        for component in components
    ) == EXPECTED_COMPONENTS[furniture_type]
    assert [component.sort_order for component in components] == list(
        range(len(components))
    )
    for component in components:
        assert component.width > 0
        assert component.height > 0
        assert component.depth is not None and component.depth > 0
        assert component.thickness is not None and component.thickness > 0
        assert component.x >= 0
        assert component.y >= 0
        assert component.z >= 0
        assert component.x + component.width <= OVERALL_WIDTH
        assert component.y + component.height <= OVERALL_HEIGHT
        assert component.z + component.depth <= OVERALL_DEPTH
        assert component.rotation == Decimal("0.0000")
        assert component.quantity == 1


@pytest.mark.parametrize("furniture_type", list(FurnitureType))
def test_default_generation_is_deterministic(furniture_type: FurnitureType) -> None:
    inputs = {
        "width_mm": Decimal("735.2500"),
        "height_mm": Decimal("981.5000"),
        "depth_mm": Decimal("447.7500"),
    }

    assert generate_default_components(
        furniture_type,
        **inputs,
    ) == generate_default_components(furniture_type, **inputs)


def test_rejects_dimensions_below_stored_geometry_precision() -> None:
    with pytest.raises(PlanGeometryRangeError, match="at least 1.0000 millimeter"):
        generate_default_components(
            FurnitureType.CHAIR,
            width_mm=Decimal("0.9999"),
            height_mm=Decimal("100"),
            depth_mm=Decimal("100"),
        )
