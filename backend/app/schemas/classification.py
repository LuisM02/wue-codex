"""Furniture classification response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureType


class FurnitureClassificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    furniture_id: UUID
    predicted_type: FurnitureType
    confidence: Decimal | None
    classifier_name: str
    classifier_version: str | None
    input_signature: str
    created_at: datetime
    updated_at: datetime
