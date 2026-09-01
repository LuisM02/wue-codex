"""Calculation-only labor-hour response schemas."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureType, LaborRuleCode


class LaborRuleBreakdownRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    rule_code: LaborRuleCode
    unit_count: int
    hours_per_unit: Decimal
    labor_hours: Decimal
    rule_description: str


class LaborQuantityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["hour"]
    rule_set: Literal["WUE v1 labor-hour estimation assumptions"]
    labor_hours: Decimal
    rules: list[LaborRuleBreakdownRead]
