"""Pure finalized-plan conversion into renderer-ready box geometry."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

from app.core.enums import (
    ComponentDepthSource,
    ComponentType,
    FurnitureType,
    PlanStatus,
)
from app.models.furniture_plan import FurniturePlan

TWO = Decimal("2")


class PlanNotFinalizedError(RuntimeError):
    """Raised when downstream 3D is requested from an editable draft."""


class ComponentDepthRequiredError(RuntimeError):
    """Raised when finalized components cannot provide a Z extent."""

    def __init__(self, component_names: list[str]) -> None:
        self.component_names = tuple(component_names)
        super().__init__(
            "3D depth is unavailable because these components have neither "
            "depth nor thickness: " + ", ".join(self.component_names)
        )


class GeometryComponent(Protocol):
    id: UUID
    component_name: str
    component_type: ComponentType
    width: Decimal
    height: Decimal
    depth: Decimal | None
    thickness: Decimal | None
    x: Decimal
    y: Decimal
    z: Decimal
    rotation: Decimal
    quantity: int
    sort_order: int


@dataclass(frozen=True, slots=True)
class Vector3D:
    x: Decimal
    y: Decimal
    z: Decimal


@dataclass(frozen=True, slots=True)
class BoxDimensions3D:
    width: Decimal
    height: Decimal
    depth: Decimal


@dataclass(frozen=True, slots=True)
class ComponentGeometry3D:
    source_component_id: UUID
    component_name: str
    component_type: ComponentType
    dimensions: BoxDimensions3D
    min_corner: Vector3D
    center: Vector3D
    depth_source: ComponentDepthSource
    rotation_degrees: Decimal
    quantity: int
    sort_order: int


@dataclass(frozen=True, slots=True)
class PlanGeometry3D:
    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["mm"]
    components: tuple[ComponentGeometry3D, ...]


def resolve_component_depth(
    component: GeometryComponent,
) -> tuple[Decimal, ComponentDepthSource] | None:
    if component.depth is not None:
        return component.depth, ComponentDepthSource.COMPONENT_DEPTH
    if component.thickness is not None:
        return component.thickness, ComponentDepthSource.THICKNESS
    return None


def build_component_geometry(
    component: GeometryComponent,
) -> ComponentGeometry3D:
    """Map an unrotated min-corner box to its renderer center."""
    resolved = resolve_component_depth(component)
    if resolved is None:
        raise ComponentDepthRequiredError([component.component_name])
    depth, depth_source = resolved
    return ComponentGeometry3D(
        source_component_id=component.id,
        component_name=component.component_name,
        component_type=component.component_type,
        dimensions=BoxDimensions3D(
            width=component.width,
            height=component.height,
            depth=depth,
        ),
        min_corner=Vector3D(x=component.x, y=component.y, z=component.z),
        center=Vector3D(
            x=component.x + component.width / TWO,
            y=component.y + component.height / TWO,
            z=component.z + depth / TWO,
        ),
        depth_source=depth_source,
        rotation_degrees=component.rotation,
        quantity=component.quantity,
        sort_order=component.sort_order,
    )


def build_plan_geometry(plan: FurniturePlan) -> PlanGeometry3D:
    """Derive 3D geometry from an immutable finalized 2D revision."""
    if plan.status != PlanStatus.FINALIZED:
        raise PlanNotFinalizedError(
            "3D reconstruction requires a finalized 2D plan"
        )
    missing_depth = [
        component.component_name
        for component in plan.components
        if component.depth is None and component.thickness is None
    ]
    if missing_depth:
        raise ComponentDepthRequiredError(missing_depth)
    return PlanGeometry3D(
        plan_id=plan.id,
        furniture_id=plan.furniture_id,
        revision=plan.revision,
        furniture_type=plan.furniture_type,
        unit="mm",
        components=tuple(
            build_component_geometry(component) for component in plan.components
        ),
    )
