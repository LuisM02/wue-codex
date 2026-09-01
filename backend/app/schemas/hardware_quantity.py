"""Calculation-only hardware quantity response schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureType, HardwareConnectionType


class HardwareConnectionQuantityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    connection_type: HardwareConnectionType
    connection_count: int
    screws_per_connection: int
    screw_quantity: int


class HardwareQuantityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    item_code: Literal["wood_screw"]
    item_name: Literal["Wood screw"]
    category: Literal["hardware"]
    unit: Literal["piece"]
    rule_name: Literal["WUE v1 wood-screw connection rule"]
    screws_per_connection: int
    connections: list[HardwareConnectionQuantityRead]
    total_connections: int
    total_quantity: int
