"""Pure calculation-only material volume estimation."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from app.core.enums import ComponentDepthSource, ComponentType, FurnitureType
from app.models.furniture_plan import FurniturePlan
from app.services.reconstruction_3d import build_plan_geometry


@dataclass(frozen=True, slots=True)
class ComponentMaterialQuantity:
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


@dataclass(frozen=True, slots=True)
class MaterialQuantity:
    plan_id: UUID
    furniture_id: UUID
    revision: int
    furniture_type: FurnitureType
    unit: Literal["mm3"]
    components: tuple[ComponentMaterialQuantity, ...]
    total_volume_mm3: Decimal


def calculate_material_quantity(plan: FurniturePlan) -> MaterialQuantity:
    """Sum canonical rectangular volumes without persisting calculated data."""
    geometry = build_plan_geometry(plan)
    components: list[ComponentMaterialQuantity] = []
    total_volume = Decimal("0")
    for item in geometry.components:
        single_piece_volume = (
            item.dimensions.width
            * item.dimensions.height
            * item.dimensions.depth
        )
        component_total = single_piece_volume * item.quantity
        components.append(
            ComponentMaterialQuantity(
                source_component_id=item.source_component_id,
                component_name=item.component_name,
                component_type=item.component_type,
                width_mm=item.dimensions.width,
                height_mm=item.dimensions.height,
                depth_mm=item.dimensions.depth,
                depth_source=item.depth_source,
                quantity=item.quantity,
                single_piece_volume_mm3=single_piece_volume,
                total_volume_mm3=component_total,
                sort_order=item.sort_order,
            )
        )
        total_volume += component_total
    return MaterialQuantity(
        plan_id=geometry.plan_id,
        furniture_id=geometry.furniture_id,
        revision=geometry.revision,
        furniture_type=geometry.furniture_type,
        unit="mm3",
        components=tuple(components),
        total_volume_mm3=total_volume,
    )
