"""Pure semantic validation for plan finalization."""

from collections import Counter
from collections.abc import Iterable
from re import ASCII, compile as compile_pattern
from typing import Protocol

from app.core.enums import ComponentType, FurnitureType

SHELF_NAME_PATTERN = compile_pattern(r"^shelf_[1-9]\d*$", flags=ASCII)
BOOKSHELF_REQUIRED_PANELS = (
    "left_side",
    "right_side",
    "top_panel",
    "bottom_panel",
    "back_panel",
)


class ComponentIdentity(Protocol):
    component_name: str
    component_type: ComponentType


class PlanSemanticValidationError(ValueError):
    """Raised with every deterministic semantic issue found in a draft."""

    def __init__(self, issues: Iterable[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("Plan cannot be finalized: " + "; ".join(self.issues))


def _validate_chair(components: list[ComponentIdentity]) -> tuple[str, ...]:
    legs = [item for item in components if item.component_type == ComponentType.LEG]
    seats = [
        item
        for item in components
        if item.component_name == "seat"
        and item.component_type == ComponentType.PANEL
    ]
    backrests = [
        item
        for item in components
        if item.component_name == "backrest"
        and item.component_type == ComponentType.PANEL
    ]
    issues: list[str] = []
    if not legs:
        issues.append("chair requires at least one leg")
    if len(seats) != 1:
        issues.append(
            f"chair requires exactly one seat panel (found {len(seats)})"
        )
    if len(backrests) != 1:
        issues.append(
            "chair requires exactly one backrest panel "
            f"(found {len(backrests)})"
        )
    return tuple(issues)


def _validate_dining_table(
    components: list[ComponentIdentity],
) -> tuple[str, ...]:
    legs = [item for item in components if item.component_type == ComponentType.LEG]
    tabletops = [
        item
        for item in components
        if item.component_name == "tabletop"
        and item.component_type == ComponentType.PANEL
    ]
    issues: list[str] = []
    if not legs:
        issues.append("dining_table requires at least one leg")
    if len(tabletops) != 1:
        issues.append(
            "dining_table requires exactly one tabletop panel "
            f"(found {len(tabletops)})"
        )
    return tuple(issues)


def _validate_bookshelf(
    components: list[ComponentIdentity],
) -> tuple[str, ...]:
    required_counts = Counter(
        item.component_name
        for item in components
        if item.component_type == ComponentType.PANEL
        and item.component_name in BOOKSHELF_REQUIRED_PANELS
    )
    shelves = [
        item
        for item in components
        if item.component_type == ComponentType.PANEL
        and SHELF_NAME_PATTERN.fullmatch(item.component_name)
    ]
    shelf_counts = Counter(item.component_name for item in shelves)
    issues: list[str] = []
    for name in BOOKSHELF_REQUIRED_PANELS:
        count = required_counts[name]
        if count != 1:
            issues.append(
                f"bookshelf requires exactly one {name} panel (found {count})"
            )
    if not shelves:
        issues.append("bookshelf requires at least one valid shelf_N panel")
    duplicate_shelves = sorted(
        name for name, count in shelf_counts.items() if count > 1
    )
    if duplicate_shelves:
        issues.append(
            "bookshelf shelf identities must be unique: "
            + ", ".join(duplicate_shelves)
        )
    return tuple(issues)


def validate_plan_components(
    furniture_type: FurnitureType,
    components: Iterable[ComponentIdentity],
) -> None:
    """Validate only the exact semantic rules approved for finalization."""
    component_list = list(components)
    if furniture_type == FurnitureType.CHAIR:
        issues = _validate_chair(component_list)
    elif furniture_type == FurnitureType.DINING_TABLE:
        issues = _validate_dining_table(component_list)
    elif furniture_type == FurnitureType.BOOKSHELF:
        issues = _validate_bookshelf(component_list)
    else:  # pragma: no cover - enum and database constraints are exhaustive
        raise ValueError(f"Unsupported furniture type: {furniture_type}")
    if issues:
        raise PlanSemanticValidationError(issues)
