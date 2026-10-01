"""Furniture image response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import FurnitureImageView, ImageInputSource


class FurnitureImageCalibrationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_left_ratio: Decimal = Field(ge=0, lt=1)
    object_top_ratio: Decimal = Field(ge=0, lt=1)
    object_width_ratio: Decimal = Field(gt=0, le=1)
    object_height_ratio: Decimal = Field(gt=0, le=1)
    is_mirrored: bool = False

    @model_validator(mode="after")
    def crop_stays_inside_image(self) -> "FurnitureImageCalibrationUpdate":
        if self.object_left_ratio + self.object_width_ratio > 1:
            raise ValueError("The horizontal object crop must stay inside the image")
        if self.object_top_ratio + self.object_height_ratio > 1:
            raise ValueError("The vertical object crop must stay inside the image")
        return self


class FurnitureImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    furniture_id: UUID
    view: FurnitureImageView
    source: ImageInputSource
    original_filename: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    pixel_width: int
    pixel_height: int
    object_left_ratio: Decimal
    object_top_ratio: Decimal
    object_width_ratio: Decimal
    object_height_ratio: Decimal
    is_mirrored: bool
    created_at: datetime
    updated_at: datetime
