"""Validation tests for dimension values, units, and provenance."""

import pytest
from pydantic import ValidationError

from app.core.enums import DimensionSource, DimensionUnit
from app.schemas.dimensions import FurnitureDimensionsWrite


def test_manual_is_the_default_trusted_source() -> None:
    payload = FurnitureDimensionsWrite(
        width="100",
        height="200",
        depth="50",
        unit="mm",
    )

    assert payload.unit is DimensionUnit.MILLIMETER
    assert payload.source is DimensionSource.MANUAL


@pytest.mark.parametrize(
    "payload",
    [
        {"width": 0, "height": 1, "depth": 1, "unit": "mm"},
        {"width": -1, "height": 1, "depth": 1, "unit": "mm"},
        {"width": 1, "height": 1, "depth": 1, "unit": "ft"},
        {
            "width": 1,
            "height": 1,
            "depth": 1,
            "unit": "mm",
            "source": "camera",
        },
        {"width": 1, "height": 1, "depth": 1, "unit": "mm", "extra": True},
    ],
)
def test_rejects_invalid_dimension_payloads(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        FurnitureDimensionsWrite.model_validate(payload)
