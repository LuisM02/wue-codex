"""Pure deterministic default geometry for supported furniture plans."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.core.enums import ComponentType, FurnitureType

GEOMETRY_QUANTUM_MM = Decimal("0.0001")
MIN_PLAN_DIMENSION_MM = Decimal("1.0000")


class PlanGeometryRangeError(ValueError):
    """Raised when overall dimensions cannot support stored plan precision."""


@dataclass(frozen=True, slots=True)
class ComponentSeed:
    component_name: str
    component_type: ComponentType
    width: Decimal
    height: Decimal
    depth: Decimal | None
    thickness: Decimal | None
    x: Decimal
    y: Decimal
    z: Decimal
    rotation: Decimal
    quantity: int
    sort_order: int


def _mm(value: Decimal) -> Decimal:
    quantized = value.quantize(GEOMETRY_QUANTUM_MM, rounding=ROUND_HALF_UP)
    if value > 0 and quantized == 0:
        return GEOMETRY_QUANTUM_MM
    return quantized


def _scaled(value: Decimal, ratio: str) -> Decimal:
    return _mm(value * Decimal(ratio))


def _component(
    name: str,
    component_type: ComponentType,
    *,
    width: Decimal,
    height: Decimal,
    depth: Decimal | None,
    thickness: Decimal | None,
    x: Decimal,
    y: Decimal,
    z: Decimal,
    sort_order: int,
) -> ComponentSeed:
    return ComponentSeed(
        component_name=name,
        component_type=component_type,
        width=_mm(width),
        height=_mm(height),
        depth=None if depth is None else _mm(depth),
        thickness=None if thickness is None else _mm(thickness),
        x=_mm(x),
        y=_mm(y),
        z=_mm(z),
        rotation=Decimal("0.0000"),
        quantity=1,
        sort_order=sort_order,
    )


def _chair(width: Decimal, height: Decimal, depth: Decimal) -> tuple[ComponentSeed, ...]:
    seat_width = _scaled(width, "0.80")
    seat_height = _scaled(height, "0.04")
    seat_depth = _scaled(depth, "0.80")
    seat_x = _scaled(width, "0.10")
    seat_y = _scaled(height, "0.45")
    seat_z = _scaled(depth, "0.10")
    leg_width = _scaled(width, "0.08")
    leg_depth = _scaled(depth, "0.08")
    right_x = _scaled(width, "0.82")
    rear_z = _scaled(depth, "0.82")
    back_depth = _scaled(depth, "0.04")

    seeds = [
        _component(
            "seat",
            ComponentType.PANEL,
            width=seat_width,
            height=seat_height,
            depth=seat_depth,
            thickness=seat_height,
            x=seat_x,
            y=seat_y,
            z=seat_z,
            sort_order=0,
        ),
        _component(
            "backrest",
            ComponentType.PANEL,
            width=seat_width,
            height=_scaled(height, "0.51"),
            depth=back_depth,
            thickness=back_depth,
            x=seat_x,
            y=_scaled(height, "0.49"),
            z=_scaled(depth, "0.86"),
            sort_order=1,
        ),
    ]
    for sort_order, name, x, z in (
        (2, "front_left_leg", seat_x, seat_z),
        (3, "front_right_leg", right_x, seat_z),
        (4, "rear_left_leg", seat_x, rear_z),
        (5, "rear_right_leg", right_x, rear_z),
    ):
        seeds.append(
            _component(
                name,
                ComponentType.LEG,
                width=leg_width,
                height=seat_y,
                depth=leg_depth,
                thickness=leg_width,
                x=x,
                y=Decimal("0"),
                z=z,
                sort_order=sort_order,
            )
        )
    return tuple(seeds)


def _dining_table(
    width: Decimal,
    height: Decimal,
    depth: Decimal,
) -> tuple[ComponentSeed, ...]:
    top_height = _scaled(height, "0.06")
    leg_height = _scaled(height, "0.94")
    leg_width = _scaled(width, "0.06")
    leg_depth = _scaled(depth, "0.06")
    left_x = _scaled(width, "0.06")
    right_x = _scaled(width, "0.88")
    front_z = _scaled(depth, "0.06")
    rear_z = _scaled(depth, "0.88")

    seeds = [
        _component(
            "tabletop",
            ComponentType.PANEL,
            width=width,
            height=top_height,
            depth=depth,
            thickness=top_height,
            x=Decimal("0"),
            y=leg_height,
            z=Decimal("0"),
            sort_order=0,
        )
    ]
    for sort_order, name, x, z in (
        (1, "front_left_leg", left_x, front_z),
        (2, "front_right_leg", right_x, front_z),
        (3, "rear_left_leg", left_x, rear_z),
        (4, "rear_right_leg", right_x, rear_z),
    ):
        seeds.append(
            _component(
                name,
                ComponentType.LEG,
                width=leg_width,
                height=leg_height,
                depth=leg_depth,
                thickness=leg_width,
                x=x,
                y=Decimal("0"),
                z=z,
                sort_order=sort_order,
            )
        )
    return tuple(seeds)


def _bookshelf(
    width: Decimal,
    height: Decimal,
    depth: Decimal,
) -> tuple[ComponentSeed, ...]:
    side_width = _scaled(width, "0.04")
    inner_width = _scaled(width, "0.92")
    panel_height = _scaled(height, "0.04")
    inner_height = _scaled(height, "0.92")
    back_depth = _scaled(depth, "0.03")
    shelf_depth = _scaled(depth, "0.97")

    return (
        _component(
            "left_side",
            ComponentType.PANEL,
            width=side_width,
            height=height,
            depth=depth,
            thickness=side_width,
            x=Decimal("0"),
            y=Decimal("0"),
            z=Decimal("0"),
            sort_order=0,
        ),
        _component(
            "right_side",
            ComponentType.PANEL,
            width=side_width,
            height=height,
            depth=depth,
            thickness=side_width,
            x=_scaled(width, "0.96"),
            y=Decimal("0"),
            z=Decimal("0"),
            sort_order=1,
        ),
        _component(
            "top_panel",
            ComponentType.PANEL,
            width=inner_width,
            height=panel_height,
            depth=depth,
            thickness=panel_height,
            x=side_width,
            y=_scaled(height, "0.96"),
            z=Decimal("0"),
            sort_order=2,
        ),
        _component(
            "bottom_panel",
            ComponentType.PANEL,
            width=inner_width,
            height=panel_height,
            depth=depth,
            thickness=panel_height,
            x=side_width,
            y=Decimal("0"),
            z=Decimal("0"),
            sort_order=3,
        ),
        _component(
            "back_panel",
            ComponentType.PANEL,
            width=inner_width,
            height=inner_height,
            depth=back_depth,
            thickness=back_depth,
            x=side_width,
            y=panel_height,
            z=shelf_depth,
            sort_order=4,
        ),
        *(
            _component(
                f"shelf_{number}",
                ComponentType.PANEL,
                width=inner_width,
                height=panel_height,
                depth=shelf_depth,
                thickness=panel_height,
                x=side_width,
                y=_scaled(height, ratio),
                z=Decimal("0"),
                sort_order=4 + number,
            )
            for number, ratio in ((1, "0.25"), (2, "0.50"), (3, "0.75"))
        ),
    )


def generate_default_components(
    furniture_type: FurnitureType,
    *,
    width_mm: Decimal,
    height_mm: Decimal,
    depth_mm: Decimal,
) -> tuple[ComponentSeed, ...]:
    """Generate stable defaults using canonical min-corner X/Y/Z positions."""
    if min(width_mm, height_mm, depth_mm) < MIN_PLAN_DIMENSION_MM:
        raise PlanGeometryRangeError(
            "Overall width, height, and depth must each be at least "
            f"{MIN_PLAN_DIMENSION_MM} millimeter for 2D generation"
        )
    if furniture_type == FurnitureType.CHAIR:
        return _chair(width_mm, height_mm, depth_mm)
    if furniture_type == FurnitureType.DINING_TABLE:
        return _dining_table(width_mm, height_mm, depth_mm)
    if furniture_type == FurnitureType.BOOKSHELF:
        return _bookshelf(width_mm, height_mm, depth_mm)
    raise ValueError(f"Unsupported furniture type: {furniture_type}")
