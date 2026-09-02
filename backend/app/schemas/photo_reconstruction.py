"""Schemas for a photo-derived, part-aware reconstruction proposal."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import ComponentType, FurnitureImageView, FurnitureType, GeometryKind
from app.schemas.plans import PositionValue, PositiveGeometryValue, ProfilePoint, RotationValue


class ReconstructionPartProposal(BaseModel):
    """Validated model-provider output for one visible furniture part."""

    model_config = ConfigDict(extra="forbid")

    component_name: Annotated[str, Field(min_length=1, max_length=200)]
    component_type: ComponentType
    geometry_kind: GeometryKind = GeometryKind.BOX
    profile_points: Annotated[list[ProfilePoint], Field(min_length=3, max_length=256)] | None = None
    width: PositiveGeometryValue
    height: PositiveGeometryValue
    depth: PositiveGeometryValue
    x: PositionValue = Decimal("0")
    y: PositionValue = Decimal("0")
    z: PositionValue = Decimal("0")
    rotation_x: RotationValue = Decimal("0")
    rotation_y: RotationValue = Decimal("0")
    rotation_z: RotationValue = Decimal("0")
    quantity: Annotated[int, Field(gt=0)] = 1
    sort_order: Annotated[int, Field(ge=0)] = 0
    confidence: Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    source_views: Annotated[list[FurnitureImageView], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_shape_and_views(self) -> "ReconstructionPartProposal":
        if len(set(self.source_views)) != len(self.source_views):
            raise ValueError("Part source views must be unique")
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


class ReconstructionPartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    reconstruction_id: UUID
    component_name: str
    component_type: ComponentType
    geometry_kind: GeometryKind
    profile_points: list[ProfilePoint] | None
    width: Decimal
    height: Decimal
    depth: Decimal
    x: Decimal
    y: Decimal
    z: Decimal
    rotation_x: Decimal
    rotation_y: Decimal
    rotation_z: Decimal
    quantity: int
    sort_order: int
    confidence: Decimal | None
    source_views: list[FurnitureImageView]
    created_at: datetime
    updated_at: datetime


class FurnitureReconstructionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    furniture_id: UUID
    input_signature: str
    furniture_type: FurnitureType
    provider_name: str
    provider_version: str | None
    confidence: Decimal | None
    warnings: list[str]
    parts: list[ReconstructionPartRead]
    created_at: datetime
    updated_at: datetime
