"""Read-only deterministic 3D reconstruction schemas."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import ComponentDepthSource, ComponentType, FurnitureType, GeometryKind
from app.schemas.plans import ProfilePoint


class Vector3DRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    x: Decimal
    y: Decimal
    z: Decimal


class BoxDimensions3DRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    width: Decimal
    height: Decimal
    depth: Decimal


class ComponentGeometry3DRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source_component_id: UUID
    component_name: str
    component_type: ComponentType
    dimensions: BoxDimensions3DRead
    min_corner: Vector3DRead
    center: Vector3DRead
    depth_source: ComponentDepthSource
    rotation_degrees: Decimal
    rotation: Vector3DRead
    geometry_kind: GeometryKind
    profile_points: list[ProfilePoint] | None
    quantity: int
    sort_order: int


class PlanGeometry3DRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["mm"]
    components: list[ComponentGeometry3DRead]
