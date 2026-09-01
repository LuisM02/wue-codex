"""Material catalog and price schema tests."""

import pytest
from pydantic import ValidationError

from app.schemas.materials import (
    MaterialCreate,
    MaterialPriceCreate,
    MaterialPriceUpdate,
    MaterialUpdate,
)


@pytest.mark.parametrize(
    ("material_type", "unit"),
    [
        ("wood", "mm3"),
        ("wood", "cm3"),
        ("wood", "m3"),
        ("wood", "board_ft"),
        ("hardware", "piece"),
    ],
)
def test_accepts_supported_material_type_and_unit_pairs(
    material_type: str,
    unit: str,
) -> None:
    material = MaterialCreate(
        material_name=" Oak ",
        material_type=material_type,
        unit=unit,
    )

    assert material.material_name == "Oak"
    assert material.is_active is True


@pytest.mark.parametrize(
    ("material_type", "unit"),
    [("wood", "piece"), ("hardware", "mm3"), ("metal", "piece")],
)
def test_rejects_invalid_material_type_and_unit_pairs(
    material_type: str,
    unit: str,
) -> None:
    with pytest.raises(ValidationError):
        MaterialCreate(
            material_name="Invalid",
            material_type=material_type,
            unit=unit,
        )


@pytest.mark.parametrize("payload", [{}, {"unit": None}, {"is_active": None}])
def test_material_update_requires_non_null_changes(payload: dict) -> None:
    with pytest.raises(ValidationError):
        MaterialUpdate.model_validate(payload)


def test_material_update_validates_pair_when_both_fields_are_present() -> None:
    with pytest.raises(ValidationError, match="incompatible"):
        MaterialUpdate(material_type="hardware", unit="m3")


def test_price_accepts_zero_and_future_effective_date() -> None:
    price = MaterialPriceCreate(
        price_per_unit="0",
        effective_date="2099-12-31",
    )

    assert str(price.price_per_unit) == "0"
    assert price.effective_date.isoformat() == "2099-12-31"


@pytest.mark.parametrize(
    "payload",
    [
        {"price_per_unit": "-0.01", "effective_date": "2026-01-01"},
        {"price_per_unit": "1.0000001", "effective_date": "2026-01-01"},
        {"price_per_unit": "1", "effective_date": "not-a-date"},
    ],
)
def test_rejects_invalid_price_input(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        MaterialPriceCreate.model_validate(payload)


@pytest.mark.parametrize("payload", [{}, {"price_per_unit": None}])
def test_price_update_requires_a_non_null_change(payload: dict) -> None:
    with pytest.raises(ValidationError):
        MaterialPriceUpdate.model_validate(payload)
