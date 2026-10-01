"""Contract tests for the local-worker classification adapter."""

import hashlib
import json

import httpx
import pytest

from app.core.enums import FurnitureImageView, FurnitureType
from app.services.classification import (
    ClassificationImage,
    ClassificationInputRejectedError,
    ClassifierUnavailableError,
    InvalidClassifierOutputError,
)
from app.services.http_classification import HttpFurnitureClassifier


def _images() -> tuple[ClassificationImage, ...]:
    return tuple(
        ClassificationImage(
            view=view,
            content_type="image/png",
            checksum_sha256=hashlib.sha256(view.value.encode()).hexdigest(),
            data=view.value.encode(),
        )
        for view in FurnitureImageView
    )


def test_http_classifier_sends_all_images_and_parses_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        assert request.url.path == "/v1/classify"
        assert all(view.value.encode() in body for view in FurnitureImageView)
        assert b"image_manifest" in body
        return httpx.Response(
            200,
            json={
                "furniture_type": "chair",
                "classifier_name": "worker-test",
                "classifier_version": "1",
                "confidence": 0.73,
            },
        )

    classifier = HttpFurnitureClassifier(
        "http://worker", 30, transport=httpx.MockTransport(handler)
    )
    result = classifier.classify(_images())
    assert result.furniture_type == FurnitureType.CHAIR
    assert str(result.confidence) == "0.73"


def test_http_classifier_preserves_worker_rejection_reason() -> None:
    classifier = HttpFurnitureClassifier(
        "http://worker",
        30,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                422, json={"detail": "The top view has the wrong orientation"}
            )
        ),
    )
    with pytest.raises(
        ClassificationInputRejectedError, match="wrong orientation"
    ):
        classifier.classify(_images())


def test_http_classifier_maps_transport_failure_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    classifier = HttpFurnitureClassifier(
        "http://worker", 30, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ClassifierUnavailableError, match="unavailable"):
        classifier.classify(_images())


def test_http_classifier_preserves_worker_failure_reason() -> None:
    classifier = HttpFurnitureClassifier(
        "http://worker",
        30,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                503, json={"detail": "SAM 2 checkpoint could not load"}
            )
        ),
    )

    with pytest.raises(ClassifierUnavailableError, match="checkpoint could not load"):
        classifier.classify(_images())


@pytest.mark.parametrize("status", [401, 403, 404, 408, 429])
def test_worker_configuration_or_busy_status_is_not_a_photo_rejection(status):
    classifier = HttpFurnitureClassifier("http://worker", 30, transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={"detail": "Internal routing detail"})
    ))
    with pytest.raises(ClassifierUnavailableError, match="could not accept the request"):
        classifier.classify(_images())


@pytest.mark.parametrize("payload", [{"detail": []}, {"detail": "  "}, {}])
def test_malformed_rejection_is_not_presented_as_photo_evidence(payload):
    classifier = HttpFurnitureClassifier("http://worker", 30, transport=httpx.MockTransport(
        lambda request: httpx.Response(422, json=payload)
    ))
    with pytest.raises(InvalidClassifierOutputError):
        classifier.classify(_images())


def test_recognition_timeout_has_an_explicit_retry_reason():
    def timeout(request):
        raise httpx.ReadTimeout("private transport detail", request=request)
    classifier = HttpFurnitureClassifier("http://worker", 30, transport=httpx.MockTransport(timeout))
    with pytest.raises(ClassifierUnavailableError, match="timed out; no new recognition result was saved"):
        classifier.classify(_images())
