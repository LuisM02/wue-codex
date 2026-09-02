"""Focused validation tests for the closed furniture type set."""

import pytest
from pydantic import ValidationError

from app.core.enums import FurnitureType
from app.schemas.furniture import FurnitureCreate, FurnitureUpdate


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("chair", FurnitureType.CHAIR),
        ("dining_table", FurnitureType.DINING_TABLE),
        ("bookshelf", FurnitureType.BOOKSHELF),
    ],
)
def test_furniture_create_accepts_only_supported_types(
    raw_value: str,
    expected: FurnitureType,
) -> None:
    furniture = FurnitureCreate(name="Item", furniture_type=raw_value)

    assert furniture.furniture_type is expected


def test_furniture_create_starts_unclassified_when_type_is_omitted() -> None:
    furniture = FurnitureCreate(name="Unknown photographed piece")

    assert furniture.furniture_type is None


@pytest.mark.parametrize("raw_value", ["bed", "sofa", "lamp_shade", "CHAIR"])
def test_furniture_create_rejects_unsupported_types(raw_value: str) -> None:
    with pytest.raises(ValidationError):
        FurnitureCreate(name="Item", furniture_type=raw_value)


@pytest.mark.parametrize("payload", [{}, {"name": None}, {"furniture_type": None}])
def test_furniture_update_rejects_invalid_mutations(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        FurnitureUpdate.model_validate(payload)
