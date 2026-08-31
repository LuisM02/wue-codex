"""Pure tests for the replaceable classifier contract."""

from decimal import Decimal

import pytest

from app.core.enums import FurnitureType
from app.services.classification import (
    ClassificationPrediction,
    ClassifierUnavailableError,
    InvalidClassifierOutputError,
    UnconfiguredFurnitureClassifier,
)


def test_prediction_normalizes_a_valid_adapter_result() -> None:
    prediction = ClassificationPrediction(
        furniture_type=FurnitureType.BOOKSHELF,
        classifier_name="  vision-model  ",
        classifier_version="  2026.08  ",
        confidence=Decimal("0.875"),
    )

    assert prediction.classifier_name == "vision-model"
    assert prediction.classifier_version == "2026.08"
    assert prediction.confidence == Decimal("0.875")


@pytest.mark.parametrize(
    "confidence",
    [Decimal("-0.0001"), Decimal("1.0001"), Decimal("NaN"), Decimal("Infinity")],
)
def test_prediction_rejects_invalid_confidence(confidence: Decimal) -> None:
    with pytest.raises(InvalidClassifierOutputError, match="between 0 and 1"):
        ClassificationPrediction(
            furniture_type=FurnitureType.CHAIR,
            classifier_name="model",
            confidence=confidence,
        )


def test_prediction_rejects_invalid_adapter_identity_or_type() -> None:
    with pytest.raises(InvalidClassifierOutputError, match="name"):
        ClassificationPrediction(
            furniture_type=FurnitureType.CHAIR,
            classifier_name=" ",
        )
    with pytest.raises(InvalidClassifierOutputError, match="unsupported type"):
        ClassificationPrediction(  # type: ignore[arg-type]
            furniture_type="bed",
            classifier_name="model",
        )


def test_default_classifier_never_fabricates_a_prediction() -> None:
    with pytest.raises(ClassifierUnavailableError, match="not configured"):
        UnconfiguredFurnitureClassifier().classify(())
