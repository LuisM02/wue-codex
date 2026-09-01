"""Read-only labor cost response schema."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import FurnitureType
from app.schemas.labor_quantity import LaborRuleBreakdownRead


class LaborCostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["hour"]
    rule_set: Literal["WUE v1 labor-hour estimation assumptions"]
    labor_hours: Decimal
    rules: list[LaborRuleBreakdownRead]
    labor_rate_id: UUID
    labor_rate_name: str
    price_id: UUID
    rate_per_hour: Decimal
    price_effective_date: date
    total_cost: Decimal
