"""Admin material catalog and price-history API schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import MaterialType, MaterialUnit
from app.schemas.common import Name

PriceValue = Annotated[
    Decimal,
    Field(ge=0, max_digits=18, decimal_places=6, allow_inf_nan=False),
]
WOOD_UNITS = {
    MaterialUnit.CUBIC_MILLIMETER,
    MaterialUnit.CUBIC_CENTIMETER,
    MaterialUnit.CUBIC_METER,
    MaterialUnit.BOARD_FOOT,
}


def is_compatible_unit(
    material_type: MaterialType,
    unit: MaterialUnit,
) -> bool:
    if material_type == MaterialType.WOOD:
        return unit in WOOD_UNITS
    return material_type == MaterialType.HARDWARE and unit == MaterialUnit.PIECE


class MaterialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_name: Name
    material_type: MaterialType
    unit: MaterialUnit
    is_active: bool = True

    @model_validator(mode="after")
    def validate_unit(self) -> Self:
        if not is_compatible_unit(self.material_type, self.unit):
            raise ValueError("Material type and unit are incompatible")
        return self


class MaterialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_name: Name | None = None
    material_type: MaterialType | None = None
    unit: MaterialUnit | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one material field must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Material {field} cannot be null")
        if (
            self.material_type is not None
            and self.unit is not None
            and not is_compatible_unit(self.material_type, self.unit)
        ):
            raise ValueError("Material type and unit are incompatible")
        return self


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    material_name: str
    material_type: MaterialType
    unit: MaterialUnit
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MaterialPriceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_per_unit: PriceValue
    effective_date: date


class MaterialPriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_per_unit: PriceValue | None = None
    effective_date: date | None = None

    @model_validator(mode="after")
    def validate_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one price field must be provided")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Material price {field} cannot be null")
        return self


class MaterialPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    material_id: UUID
    price_per_unit: Decimal
    unit: MaterialUnit
    effective_date: date
    created_at: datetime
    updated_at: datetime
