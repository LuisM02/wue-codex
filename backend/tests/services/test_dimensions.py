"""Pure Decimal conversion and canonical-axis tests."""

from decimal import Decimal

import pytest

from app.core.enums import DimensionUnit
from app.schemas.dimensions import FurnitureDimensionsWrite
from app.services.dimensions import (
    DimensionRangeError,
    canonicalize,
    convert_from_mm,
    convert_to_mm,
)


@pytest.mark.parametrize(
    ("value", "unit", "expected_mm"),
    [
        ("1.23456", DimensionUnit.MILLIMETER, "1.2346"),
        ("12.34", DimensionUnit.CENTIMETER, "123.4000"),
        ("0.75", DimensionUnit.METER, "750.0000"),
        ("2", DimensionUnit.INCH, "50.8000"),
    ],
)
def test_converts_supported_units_to_decimal_millimeters(
    value: str,
    unit: DimensionUnit,
    expected_mm: str,
) -> None:
    assert convert_to_mm(Decimal(value), unit) == Decimal(expected_mm)


def test_canonical_axes_are_width_x_height_y_depth_z() -> None:
    payload = FurnitureDimensionsWrite(
        width=Decimal("100"),
        height=Decimal("200"),
        depth=Decimal("300"),
        unit="cm",
    )

    canonical = canonicalize(payload)

    assert canonical.width_mm == Decimal("1000.0000")
    assert canonical.height_mm == Decimal("2000.0000")
    assert canonical.depth_mm == Decimal("3000.0000")


def test_converts_canonical_values_back_without_hidden_float_math() -> None:
    assert convert_from_mm(Decimal("25.4000"), DimensionUnit.INCH) == Decimal("1.000")
    assert convert_from_mm(Decimal("1000.0000"), DimensionUnit.METER) == Decimal(
        "1.0000"
    )


def test_rejects_canonical_overflow() -> None:
    with pytest.raises(DimensionRangeError, match="Converted dimension"):
        convert_to_mm(Decimal("10000000"), DimensionUnit.METER)
