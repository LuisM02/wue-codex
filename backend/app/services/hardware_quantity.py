"""Pure rule-based wood-screw quantity estimation."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from app.core.enums import (
    ComponentType,
    FurnitureType,
    HardwareConnectionType,
    PlanStatus,
)
from app.services.plan_validation import SHELF_NAME_PATTERN

WOOD_SCREWS_PER_CONNECTION = 2


class HardwareComponent(Protocol):
    component_name: str
    component_type: ComponentType
    quantity: int


class HardwarePlan(Protocol):
    id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    status: PlanStatus
    components: Sequence[HardwareComponent]


class PlanNotFinalizedError(RuntimeError):
    """Raised when hardware estimation is requested from an editable draft."""


@dataclass(frozen=True, slots=True)
class HardwareConnectionQuantity:
    connection_type: HardwareConnectionType
    connection_count: int
    screws_per_connection: int
    screw_quantity: int


@dataclass(frozen=True, slots=True)
class HardwareQuantity:
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
    connections: tuple[HardwareConnectionQuantity, ...]
    total_connections: int
    total_quantity: int


def _physical_count(
    components: Sequence[HardwareComponent],
    *,
    component_type: ComponentType,
    component_names: frozenset[str] | None = None,
) -> int:
    return sum(
        component.quantity
        for component in components
        if component.component_type == component_type
        and (
            component_names is None
            or component.component_name in component_names
        )
    )


def _connection_group(
    connection_type: HardwareConnectionType,
    connection_count: int,
) -> HardwareConnectionQuantity:
    return HardwareConnectionQuantity(
        connection_type=connection_type,
        connection_count=connection_count,
        screws_per_connection=WOOD_SCREWS_PER_CONNECTION,
        screw_quantity=connection_count * WOOD_SCREWS_PER_CONNECTION,
    )


def _chair_connections(
    components: Sequence[HardwareComponent],
) -> tuple[HardwareConnectionQuantity, ...]:
    leg_count = _physical_count(
        components,
        component_type=ComponentType.LEG,
    )
    backrest_count = _physical_count(
        components,
        component_type=ComponentType.PANEL,
        component_names=frozenset({"backrest"}),
    )
    return (
        _connection_group(HardwareConnectionType.LEG, leg_count),
        _connection_group(HardwareConnectionType.BACKREST, backrest_count),
    )


def _dining_table_connections(
    components: Sequence[HardwareComponent],
) -> tuple[HardwareConnectionQuantity, ...]:
    leg_count = _physical_count(
        components,
        component_type=ComponentType.LEG,
    )
    return (_connection_group(HardwareConnectionType.LEG, leg_count),)


def _bookshelf_connections(
    components: Sequence[HardwareComponent],
) -> tuple[HardwareConnectionQuantity, ...]:
    side_count = _physical_count(
        components,
        component_type=ComponentType.PANEL,
        component_names=frozenset({"left_side", "right_side"}),
    )
    top_bottom_count = _physical_count(
        components,
        component_type=ComponentType.PANEL,
        component_names=frozenset({"top_panel", "bottom_panel"}),
    )
    shelf_count = sum(
        component.quantity
        for component in components
        if component.component_type == ComponentType.PANEL
        and SHELF_NAME_PATTERN.fullmatch(component.component_name)
    )
    return (
        _connection_group(
            HardwareConnectionType.CARCASS,
            side_count * top_bottom_count,
        ),
        _connection_group(
            HardwareConnectionType.SHELF,
            shelf_count * side_count,
        ),
    )


def calculate_hardware_quantity(plan: HardwarePlan) -> HardwareQuantity:
    """Apply the documented WUE v1 rules without persisting an estimate."""
    if plan.status != PlanStatus.FINALIZED:
        raise PlanNotFinalizedError(
            "Hardware quantity estimation requires a finalized 2D plan"
        )

    if plan.furniture_type == FurnitureType.CHAIR:
        connections = _chair_connections(plan.components)
    elif plan.furniture_type == FurnitureType.DINING_TABLE:
        connections = _dining_table_connections(plan.components)
    elif plan.furniture_type == FurnitureType.BOOKSHELF:
        connections = _bookshelf_connections(plan.components)
    else:  # pragma: no cover - enum and database constraints are exhaustive
        raise ValueError(f"Unsupported furniture type: {plan.furniture_type}")

    total_connections = sum(item.connection_count for item in connections)
    return HardwareQuantity(
        plan_id=plan.id,
        furniture_id=plan.furniture_id,
        revision=plan.revision,
        furniture_type=plan.furniture_type,
        item_code="wood_screw",
        item_name="Wood screw",
        category="hardware",
        unit="piece",
        rule_name="WUE v1 wood-screw connection rule",
        screws_per_connection=WOOD_SCREWS_PER_CONNECTION,
        connections=connections,
        total_connections=total_connections,
        total_quantity=total_connections * WOOD_SCREWS_PER_CONNECTION,
    )
