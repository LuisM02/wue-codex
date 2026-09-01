"""Admin labor-rate catalog and dated-price schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Name

HourlyRateValue = Annotated[
    Decimal,
    Field(ge=0, max_digits=18, decimal_places=6, allow_inf_nan=False),
]


class LaborRateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_name: Name
    is_active: bool = True


class LaborRateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_name: Name | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "LaborRateUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one labor rate field must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Labor rate {field} cannot be null")
        return self


class LaborRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    rate_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LaborRatePriceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_per_hour: HourlyRateValue
    effective_date: date


class LaborRatePriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_per_hour: HourlyRateValue | None = None
    effective_date: date | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "LaborRatePriceUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one labor rate price field must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Labor rate price {field} cannot be null")
        return self


class LaborRatePriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    labor_rate_id: UUID
    rate_per_hour: Decimal
    effective_date: date
    created_at: datetime
    updated_at: datetime
