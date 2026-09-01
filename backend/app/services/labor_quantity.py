"""Pure rule-based WUE v1 labor-hour estimation."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

from app.core.enums import (
    ComponentType,
    FurnitureType,
    LaborRuleCode,
    PlanStatus,
)
from app.services.plan_validation import (
    BOOKSHELF_REQUIRED_PANELS,
    SHELF_NAME_PATTERN,
)

LABOR_RULE_SET = "WUE v1 labor-hour estimation assumptions"


class LaborComponent(Protocol):
    component_name: str
    component_type: ComponentType


class LaborPlan(Protocol):
    id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    status: PlanStatus
    components: Sequence[LaborComponent]


class PlanNotFinalizedError(RuntimeError):
    """Raised when labor estimation is requested from an editable draft."""


@dataclass(frozen=True, slots=True)
class LaborRuleBreakdown:
    rule_code: LaborRuleCode
    unit_count: int
    hours_per_unit: Decimal
    labor_hours: Decimal
    rule_description: str


@dataclass(frozen=True, slots=True)
class LaborQuantity:
    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["hour"]
    rule_set: Literal["WUE v1 labor-hour estimation assumptions"]
    labor_hours: Decimal
    rules: tuple[LaborRuleBreakdown, ...]


def _rule(
    rule_code: LaborRuleCode,
    unit_count: int,
    hours_per_unit: Decimal,
    description: str,
) -> LaborRuleBreakdown:
    return LaborRuleBreakdown(
        rule_code=rule_code,
        unit_count=unit_count,
        hours_per_unit=hours_per_unit,
        labor_hours=Decimal(unit_count) * hours_per_unit,
        rule_description=description,
    )


def _chair_rules(
    components: Sequence[LaborComponent],
) -> tuple[LaborRuleBreakdown, ...]:
    leg_count = sum(
        1 for item in components if item.component_type == ComponentType.LEG
    )
    backrest_count = sum(
        1
        for item in components
        if item.component_name == "backrest"
        and item.component_type == ComponentType.PANEL
    )
    return (
        _rule(
            LaborRuleCode.CHAIR_BASE_ASSEMBLY,
            1,
            Decimal("1.00"),
            "1 base assembly occurrence x 1.00 hour",
        ),
        _rule(
            LaborRuleCode.CHAIR_LEG_WORK,
            leg_count,
            Decimal("0.25"),
            f"{leg_count} leg(s) x 0.25 hour per leg",
        ),
        _rule(
            LaborRuleCode.CHAIR_BACKREST_WORK,
            backrest_count,
            Decimal("0.50"),
            f"{backrest_count} backrest(s) x 0.50 hour per backrest",
        ),
    )


def _dining_table_rules(
    components: Sequence[LaborComponent],
) -> tuple[LaborRuleBreakdown, ...]:
    leg_count = sum(
        1 for item in components if item.component_type == ComponentType.LEG
    )
    tabletop_count = sum(
        1
        for item in components
        if item.component_name == "tabletop"
        and item.component_type == ComponentType.PANEL
    )
    return (
        _rule(
            LaborRuleCode.DINING_TABLE_BASE_ASSEMBLY,
            1,
            Decimal("1.50"),
            "1 base assembly occurrence x 1.50 hours",
        ),
        _rule(
            LaborRuleCode.DINING_TABLE_LEG_WORK,
            leg_count,
            Decimal("0.30"),
            f"{leg_count} leg(s) x 0.30 hour per leg",
        ),
        _rule(
            LaborRuleCode.DINING_TABLE_TABLETOP_WORK,
            tabletop_count,
            Decimal("0.50"),
            f"{tabletop_count} tabletop(s) x 0.50 hour per tabletop",
        ),
    )


def _bookshelf_rules(
    components: Sequence[LaborComponent],
) -> tuple[LaborRuleBreakdown, ...]:
    carcass_panel_count = sum(
        1
        for item in components
        if item.component_name in BOOKSHELF_REQUIRED_PANELS
        and item.component_type == ComponentType.PANEL
    )
    shelf_count = sum(
        1
        for item in components
        if SHELF_NAME_PATTERN.fullmatch(item.component_name)
        and item.component_type == ComponentType.PANEL
    )
    return (
        _rule(
            LaborRuleCode.BOOKSHELF_BASE_ASSEMBLY,
            1,
            Decimal("1.50"),
            "1 base assembly occurrence x 1.50 hours",
        ),
        _rule(
            LaborRuleCode.BOOKSHELF_CARCASS_PANEL_WORK,
            carcass_panel_count,
            Decimal("0.25"),
            f"{carcass_panel_count} carcass panel(s) x 0.25 hour per panel",
        ),
        _rule(
            LaborRuleCode.BOOKSHELF_SHELF_WORK,
            shelf_count,
            Decimal("0.20"),
            f"{shelf_count} shelf(s) x 0.20 hour per shelf",
        ),
    )


def calculate_labor_quantity(plan: LaborPlan) -> LaborQuantity:
    """Apply approved assumptions to one immutable finalized plan revision."""
    if plan.status != PlanStatus.FINALIZED:
        raise PlanNotFinalizedError(
            "Labor quantity estimation requires a finalized 2D plan"
        )

    if plan.furniture_type == FurnitureType.CHAIR:
        rules = _chair_rules(plan.components)
    elif plan.furniture_type == FurnitureType.DINING_TABLE:
        rules = _dining_table_rules(plan.components)
    elif plan.furniture_type == FurnitureType.BOOKSHELF:
        rules = _bookshelf_rules(plan.components)
    else:  # pragma: no cover - enum and database constraints are exhaustive
        raise ValueError(f"Unsupported furniture type: {plan.furniture_type}")

    return LaborQuantity(
        plan_id=plan.id,
        furniture_id=plan.furniture_id,
        revision=plan.revision,
        furniture_type=plan.furniture_type,
        unit="hour",
        rule_set=LABOR_RULE_SET,
        labor_hours=sum(
            (item.labor_hours for item in rules),
            start=Decimal("0"),
        ),
        rules=rules,
    )
