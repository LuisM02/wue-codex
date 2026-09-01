"""PostgreSQL constraints for materials and dated prices."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.material import Material
from app.models.material_price import MaterialPrice
from app.schemas.materials import MaterialCreate, MaterialPriceCreate
from app.services.materials import create_material, create_price

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "overrides",
    [
        {"material_type": "metal"},
        {"unit": "kg"},
        {"material_type": "wood", "unit": "piece"},
        {"material_type": "hardware", "unit": "m3"},
    ],
)
def test_postgresql_rejects_invalid_material_category_or_unit(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "id": str(uuid4()),
        "material_name": f"Invalid {uuid4()}",
        "material_type": "wood",
        "unit": "mm3",
        "is_active": True,
    }
    values.update(overrides)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO materials (
                        id, material_name, material_type, unit, is_active
                    ) VALUES (
                        :id, :material_name, :material_type, :unit, :is_active
                    )
                    """
                ),
                values,
            )


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_per_unit": "-0.000001"},
        {"unit": "kg"},
    ],
)
def test_postgresql_rejects_invalid_price_state(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    material = create_material(
        db_session,
        MaterialCreate(
            material_name=f"Price constraints {uuid4()}",
            material_type="wood",
            unit="m3",
        ),
    )
    values: dict[str, object] = {
        "id": str(uuid4()),
        "material_id": str(material.id),
        "price_per_unit": "1.000000",
        "unit": "m3",
        "effective_date": "2026-01-01",
    }
    values.update(overrides)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO material_prices (
                        id, material_id, price_per_unit, unit, effective_date
                    ) VALUES (
                        :id, :material_id, :price_per_unit, :unit, :effective_date
                    )
                    """
                ),
                values,
            )


def test_deleting_material_cascades_to_price_history(
    db_session: Session,
) -> None:
    material = create_material(
        db_session,
        MaterialCreate(
            material_name=f"Cascade {uuid4()}",
            material_type="wood",
            unit="board_ft",
        ),
    )
    price = create_price(
        db_session,
        material,
        MaterialPriceCreate(
            price_per_unit="12.5",
            effective_date="2026-01-01",
        ),
    )
    price_id = price.id

    db_session.delete(material)
    db_session.commit()

    assert db_session.get(Material, material.id) is None
    assert db_session.get(MaterialPrice, price_id) is None
    assert db_session.scalar(
        select(func.count()).select_from(MaterialPrice).where(
            MaterialPrice.material_id == material.id
        )
    ) == 0
