"""Overall furniture dimension API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DimensionSource, DimensionUnit

DimensionValue = Annotated[
    Decimal,
    Field(gt=0, max_digits=14, decimal_places=6, allow_inf_nan=False),
]


class FurnitureDimensionsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: DimensionValue
    height: DimensionValue
    depth: DimensionValue
    unit: DimensionUnit
    source: DimensionSource = DimensionSource.MANUAL


class FurnitureDimensionsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    furniture_id: UUID
    width_mm: Decimal
    height_mm: Decimal
    depth_mm: Decimal
    unit: DimensionUnit
    source: DimensionSource
    is_locked: bool
    locked_at: datetime | None
    created_at: datetime
    updated_at: datetime
