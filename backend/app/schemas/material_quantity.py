"""Calculation-only material volume response schemas."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import ComponentDepthSource, ComponentType, FurnitureType


class ComponentMaterialQuantityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    source_component_id: UUID
    component_name: str
    component_type: ComponentType
    width_mm: Decimal
    height_mm: Decimal
    depth_mm: Decimal
    depth_source: ComponentDepthSource
    quantity: int
    single_piece_volume_mm3: Decimal
    total_volume_mm3: Decimal
    sort_order: int


class MaterialQuantityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["mm3"]
    components: list[ComponentMaterialQuantityRead]
    total_volume_mm3: Decimal
