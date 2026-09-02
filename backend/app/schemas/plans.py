"""Parametric furniture plan API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.enums import ComponentType, FurnitureImageView, FurnitureType, GeometryKind, PlanStatus

ComponentName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
PositiveGeometryValue = Annotated[
    Decimal,
    Field(gt=0, max_digits=14, decimal_places=4, allow_inf_nan=False),
]
PositionValue = Annotated[
    Decimal,
    Field(max_digits=14, decimal_places=4, allow_inf_nan=False),
]
RotationValue = Annotated[
    Decimal,
    Field(max_digits=9, decimal_places=4, allow_inf_nan=False),
]


class ProfilePoint(BaseModel):
    """One local millimeter coordinate in a component's front-facing XY outline."""

    model_config = ConfigDict(extra="forbid")

    u: PositionValue
    v: PositionValue


class ComponentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: ComponentName
    component_type: ComponentType
    width: PositiveGeometryValue
    height: PositiveGeometryValue
    depth: PositiveGeometryValue | None = None
    thickness: PositiveGeometryValue | None = None
    x: PositionValue = Decimal("0")
    y: PositionValue = Decimal("0")
    z: PositionValue = Decimal("0")
    rotation: RotationValue = Decimal("0")
    rotation_x: RotationValue = Decimal("0")
    rotation_y: RotationValue = Decimal("0")
    rotation_z: RotationValue = Decimal("0")
    geometry_kind: GeometryKind = GeometryKind.BOX
    profile_points: Annotated[list[ProfilePoint], Field(min_length=3, max_length=256)] | None = None
    quantity: Annotated[int, Field(gt=0)] = 1
    sort_order: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        if self.geometry_kind == GeometryKind.BOX and self.profile_points is not None:
            raise ValueError("Box geometry cannot contain profile points")
        if self.geometry_kind == GeometryKind.EXTRUDED_PROFILE:
            if self.profile_points is None:
                raise ValueError("Extruded-profile geometry requires at least three points")
            if any(
                point.u < 0
                or point.v < 0
                or point.u > self.width
                or point.v > self.height
                for point in self.profile_points
            ):
                raise ValueError("Profile points must stay within the part width and height")
            twice_area = sum(
                point.u * self.profile_points[(index + 1) % len(self.profile_points)].v
                - self.profile_points[(index + 1) % len(self.profile_points)].u * point.v
                for index, point in enumerate(self.profile_points)
            )
            if twice_area == 0:
                raise ValueError("Profile points must enclose a non-zero area")
        return self


class ComponentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: ComponentName | None = None
    component_type: ComponentType | None = None
    width: PositiveGeometryValue | None = None
    height: PositiveGeometryValue | None = None
    depth: PositiveGeometryValue | None = None
    thickness: PositiveGeometryValue | None = None
    x: PositionValue | None = None
    y: PositionValue | None = None
    z: PositionValue | None = None
    rotation: RotationValue | None = None
    rotation_x: RotationValue | None = None
    rotation_y: RotationValue | None = None
    rotation_z: RotationValue | None = None
    geometry_kind: GeometryKind | None = None
    profile_points: Annotated[list[ProfilePoint], Field(min_length=3, max_length=256)] | None = None
    quantity: Annotated[int, Field(gt=0)] | None = None
    sort_order: Annotated[int, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one component field must be provided")
        nullable_fields = {"depth", "thickness", "profile_points"}
        for field in self.model_fields_set - nullable_fields:
            if getattr(self, field) is None:
                raise ValueError(f"Component {field} cannot be null")
        return self


class ComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    plan_id: UUID
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
    rotation_x: Decimal
    rotation_y: Decimal
    rotation_z: Decimal
    geometry_kind: GeometryKind
    profile_points: list[ProfilePoint] | None
    source_reconstruction_part_id: UUID | None
    source_confidence: Decimal | None
    source_views: list[FurnitureImageView]
    quantity: int
    sort_order: int
    created_at: datetime
    updated_at: datetime


class FurniturePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    furniture_id: UUID
    revision: int
    status: PlanStatus
    furniture_type: FurnitureType
    source_reconstruction_id: UUID | None
    components: list[ComponentRead]
    created_at: datetime
    updated_at: datetime
