"""Pure canonical material-volume calculation tests."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentType, FurnitureType, GeometryKind, PlanStatus
from app.services.material_quantity import calculate_material_quantity
from app.services.reconstruction_3d import (
    ComponentDepthRequiredError,
    PlanNotFinalizedError,
)


@dataclass(frozen=True)
class Component:
    id: UUID
    component_name: str
    component_type: ComponentType
    width: Decimal
    height: Decimal
    depth: Decimal | None
    thickness: Decimal | None
    x: Decimal = Decimal("0")
    y: Decimal = Decimal("0")
    z: Decimal = Decimal("0")
    rotation: Decimal = Decimal("0")
    rotation_x: Decimal = Decimal("0")
    rotation_y: Decimal = Decimal("0")
    rotation_z: Decimal = Decimal("0")
    geometry_kind: GeometryKind = GeometryKind.BOX
    profile_points: list[dict[str, str]] | None = None
    quantity: int = 1
    sort_order: int = 0


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
    depth: str | None,
    thickness: str | None = None,
    quantity: int = 1,
    sort_order: int = 0,
) -> Component:
    return Component(
        id=uuid4(),
        component_name=name,
        component_type=ComponentType.PANEL,
        width=Decimal(width),
        height=Decimal(height),
        depth=None if depth is None else Decimal(depth),
        thickness=None if thickness is None else Decimal(thickness),
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
        revision=3,
        furniture_type=FurnitureType.BOOKSHELF,
        status=status,
        components=components,
    )


def test_calculates_single_piece_quantity_and_exact_total_volume() -> None:
    direct = component(
        "direct",
        width="2",
        height="3",
        depth="4",
        quantity=3,
    )
    fallback = component(
        "fallback",
        width="1.5",
        height="2",
        depth=None,
        thickness="5",
        quantity=2,
        sort_order=1,
    )
    source = plan(direct, fallback)

    result = calculate_material_quantity(source)  # type: ignore[arg-type]

    assert result.unit == "mm3"
    assert result.total_volume_mm3 == Decimal("102.0")
    first, second = result.components
    assert first.single_piece_volume_mm3 == Decimal("24")
    assert first.total_volume_mm3 == Decimal("72")
    assert first.depth_source.value == "component_depth"
    assert second.single_piece_volume_mm3 == Decimal("15.0")
    assert second.total_volume_mm3 == Decimal("30.0")
    assert second.depth_source.value == "thickness"


def test_calculation_is_deterministic_read_only_and_ignores_position() -> None:
    source_component = component(
        "panel",
        width="10.0001",
        height="20.0002",
        depth="30.0003",
    )
    source = plan(source_component)

    first = calculate_material_quantity(source)  # type: ignore[arg-type]
    second = calculate_material_quantity(source)  # type: ignore[arg-type]

    expected = Decimal("10.0001") * Decimal("20.0002") * Decimal("30.0003")
    assert first == second
    assert first.total_volume_mm3 == expected
    assert first.components[0].source_component_id == source_component.id
    assert source.components == (source_component,)


def test_extruded_profile_uses_polygon_area_instead_of_bounding_box() -> None:
    triangle = component("profile", width="10", height="10", depth="4")
    object.__setattr__(triangle, "geometry_kind", GeometryKind.EXTRUDED_PROFILE)
    object.__setattr__(
        triangle,
        "profile_points",
        [{"u": "0", "v": "0"}, {"u": "10", "v": "0"}, {"u": "0", "v": "10"}],
    )

    result = calculate_material_quantity(plan(triangle))  # type: ignore[arg-type]

    assert result.total_volume_mm3 == Decimal("200")


def test_draft_plan_is_rejected() -> None:
    source = plan(
        component("panel", width="1", height="1", depth="1"),
        status=PlanStatus.DRAFT,
    )

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        calculate_material_quantity(source)  # type: ignore[arg-type]


def test_missing_depth_is_rejected_without_partial_result() -> None:
    source = plan(
        component("panel", width="1", height="1", depth=None),
    )

    with pytest.raises(ComponentDepthRequiredError, match="neither depth"):
        calculate_material_quantity(source)  # type: ignore[arg-type]
