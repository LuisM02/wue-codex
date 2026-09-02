"""Furniture API schemas."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import FurnitureType
from app.schemas.common import Name


class FurnitureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    furniture_type: FurnitureType | None = None


class FurnitureUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    furniture_type: FurnitureType | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one furniture field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Furniture name cannot be null")
        if "furniture_type" in self.model_fields_set and self.furniture_type is None:
            raise ValueError("Furniture type cannot be null")
        return self


class FurnitureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    project_id: UUID
    name: str
    furniture_type: FurnitureType | None
    created_at: datetime
    updated_at: datetime
