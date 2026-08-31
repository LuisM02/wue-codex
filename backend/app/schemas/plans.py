"""Parametric furniture plan API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.enums import ComponentType, FurnitureType, PlanStatus

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
    quantity: Annotated[int, Field(gt=0)] = 1
    sort_order: Annotated[int, Field(ge=0)] = 0


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
    quantity: Annotated[int, Field(gt=0)] | None = None
    sort_order: Annotated[int, Field(ge=0)] | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one component field must be provided")
        nullable_fields = {"depth", "thickness"}
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
    components: list[ComponentRead]
    created_at: datetime
    updated_at: datetime
