"""Pure deterministic finalized-plan 3D conversion tests."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.core.enums import ComponentDepthSource, ComponentType, FurnitureType, GeometryKind, PlanStatus
from app.services.reconstruction_3d import (
    ComponentDepthRequiredError,
    PlanNotFinalizedError,
    build_component_geometry,
    build_plan_geometry,
)


@dataclass(frozen=True)
class Component:
    id: UUID
    component_name: str = "panel"
    component_type: ComponentType = ComponentType.PANEL
    width: Decimal = Decimal("101.0001")
    height: Decimal = Decimal("40.0000")
    depth: Decimal | None = Decimal("11.0001")
    thickness: Decimal | None = Decimal("22.0000")
    x: Decimal = Decimal("-10.0000")
    y: Decimal = Decimal("5.0000")
    z: Decimal = Decimal("-5.0000")
    rotation: Decimal = Decimal("45.5000")
    rotation_x: Decimal = Decimal("0")
    rotation_y: Decimal = Decimal("45.5000")
    rotation_z: Decimal = Decimal("0")
    geometry_kind: GeometryKind = GeometryKind.BOX
    profile_points: list[dict[str, str]] | None = None
    quantity: int = 3
    sort_order: int = 7


@dataclass(frozen=True)
class Plan:
    id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    status: PlanStatus
    components: tuple[Component, ...]


def component(**overrides: object) -> Component:
    values: dict[str, object] = {"id": uuid4()}
    values.update(overrides)
    return Component(**values)


def plan(*components: Component, status: PlanStatus = PlanStatus.FINALIZED) -> Plan:
    return Plan(
        id=uuid4(),
        furniture_id=uuid4(),
        revision=2,
        furniture_type=FurnitureType.CHAIR,
        status=status,
        components=components,
    )


def test_maps_dimensions_and_min_corner_to_exact_box_center() -> None:
    source = component()

    result = build_component_geometry(source)

    assert result.source_component_id == source.id
    assert result.dimensions.width == Decimal("101.0001")
    assert result.dimensions.height == Decimal("40.0000")
    assert result.dimensions.depth == Decimal("11.0001")
    assert result.min_corner.x == Decimal("-10.0000")
    assert result.min_corner.y == Decimal("5.0000")
    assert result.min_corner.z == Decimal("-5.0000")
    assert result.center.x == Decimal("40.50005")
    assert result.center.y == Decimal("25.0000")
    assert result.center.z == Decimal("0.50005")
    assert result.depth_source == ComponentDepthSource.COMPONENT_DEPTH
    assert result.rotation_degrees == Decimal("45.5000")
    assert result.rotation.y == Decimal("45.5000")
    assert result.geometry_kind == GeometryKind.BOX
    assert result.profile_points is None
    assert result.quantity == 3
    assert result.sort_order == 7


def test_depth_takes_precedence_over_thickness() -> None:
    result = build_component_geometry(
        component(depth=Decimal("30"), thickness=Decimal("900"))
    )

    assert result.dimensions.depth == Decimal("30")
    assert result.depth_source == ComponentDepthSource.COMPONENT_DEPTH


def test_thickness_is_used_only_when_depth_is_absent() -> None:
    result = build_component_geometry(
        component(depth=None, thickness=Decimal("18.5000"))
    )

    assert result.dimensions.depth == Decimal("18.5000")
    assert result.center.z == Decimal("4.2500")
    assert result.depth_source == ComponentDepthSource.THICKNESS


def test_component_without_depth_or_thickness_fails_clearly() -> None:
    with pytest.raises(ComponentDepthRequiredError) as exc_info:
        build_component_geometry(
            component(component_name="backrest", depth=None, thickness=None)
        )

    assert exc_info.value.component_names == ("backrest",)
    assert str(exc_info.value).endswith("backrest")


def test_plan_reports_every_component_missing_extrusion_depth() -> None:
    source = plan(
        component(component_name="seat", depth=None, thickness=None),
        component(component_name="backrest", depth=None, thickness=None),
    )

    with pytest.raises(ComponentDepthRequiredError) as exc_info:
        build_plan_geometry(source)  # type: ignore[arg-type]

    assert exc_info.value.component_names == ("seat", "backrest")


def test_draft_plan_cannot_drive_3d_reconstruction() -> None:
    source = plan(component(), status=PlanStatus.DRAFT)

    with pytest.raises(PlanNotFinalizedError, match="requires a finalized"):
        build_plan_geometry(source)  # type: ignore[arg-type]


def test_plan_conversion_is_deterministic_and_read_only() -> None:
    first = component(component_name="first", sort_order=0)
    second = component(component_name="second", sort_order=1, depth=None)
    source = plan(first, second)

    initial = build_plan_geometry(source)  # type: ignore[arg-type]
    repeated = build_plan_geometry(source)  # type: ignore[arg-type]

    assert initial == repeated
    assert initial.plan_id == source.id
    assert initial.furniture_id == source.furniture_id
    assert initial.revision == 2
    assert initial.furniture_type == FurnitureType.CHAIR
    assert initial.unit == "mm"
    assert [item.component_name for item in initial.components] == [
        "first",
        "second",
    ]
    assert source.components == (first, second)
