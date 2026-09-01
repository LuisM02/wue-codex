"""Labor-rate catalog schema tests."""

import pytest
from pydantic import ValidationError

from app.schemas.labor_rates import (
    LaborRateCreate,
    LaborRatePriceCreate,
    LaborRatePriceUpdate,
    LaborRateUpdate,
)


def test_rate_create_strips_name_and_defaults_active() -> None:
    rate = LaborRateCreate(rate_name=" Standard woodworking ")

    assert rate.rate_name == "Standard woodworking"
    assert rate.is_active is True


@pytest.mark.parametrize("payload", [{}, {"rate_name": None}, {"is_active": None}])
def test_rate_update_requires_non_null_changes(payload: dict) -> None:
    with pytest.raises(ValidationError):
        LaborRateUpdate.model_validate(payload)


def test_price_accepts_zero_and_future_effective_date() -> None:
    price = LaborRatePriceCreate(
        rate_per_hour="0",
        effective_date="2099-12-31",
    )

    assert str(price.rate_per_hour) == "0"
    assert price.effective_date.isoformat() == "2099-12-31"


@pytest.mark.parametrize(
    "payload",
    [
        {"rate_per_hour": "-0.01", "effective_date": "2026-01-01"},
        {"rate_per_hour": "1.0000001", "effective_date": "2026-01-01"},
        {"rate_per_hour": "1", "effective_date": "invalid"},
    ],
)
def test_rejects_invalid_price_input(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        LaborRatePriceCreate.model_validate(payload)


@pytest.mark.parametrize("payload", [{}, {"rate_per_hour": None}])
def test_price_update_requires_non_null_change(payload: dict) -> None:
    with pytest.raises(ValidationError):
        LaborRatePriceUpdate.model_validate(payload)
