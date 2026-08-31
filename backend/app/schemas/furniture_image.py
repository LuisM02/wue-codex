"""Furniture image response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureImageView, ImageInputSource


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
    created_at: datetime
    updated_at: datetime
