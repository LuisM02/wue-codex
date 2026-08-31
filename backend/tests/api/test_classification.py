"""Real PostgreSQL/filesystem API tests for classification orchestration."""

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_furniture_classifier
from app.core.enums import FurnitureImageView, FurnitureType
from app.main import app
from app.services.classification import (
    ClassificationImage,
    ClassificationPrediction,
)
from app.services.image_storage import LocalImageStorage

pytestmark = pytest.mark.integration


class RecordingClassifier:
    def __init__(self, prediction: ClassificationPrediction) -> None:
        self.prediction = prediction
        self.calls: list[tuple[ClassificationImage, ...]] = []

    def classify(
        self,
        images: tuple[ClassificationImage, ...],
    ) -> ClassificationPrediction:
        self.calls.append(images)
        return self.prediction


class InvalidObjectClassifier:
    def classify(self, images: tuple[ClassificationImage, ...]):
        return {"furniture_type": "chair"}


def create_furniture(client: TestClient) -> str:
    project = client.post("/api/v1/projects", json={"name": "Classification"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Unknown design", "furniture_type": "chair"},
    )
    return furniture.json()["id"]


def upload_views(
    client: TestClient,
    furniture_id: str,
    image_bytes_factory: Callable[..., bytes],
    views: tuple[str, ...] = ("front", "back", "left", "right", "top"),
) -> dict[str, bytes]:
    uploaded: dict[str, bytes] = {}
    for view in views:
        data = image_bytes_factory("PNG")
        uploaded[view] = data
        response = client.post(
            f"/api/v1/furniture/{furniture_id}/images/{view}",
            files={"file": (f"{view}.png", data, "image/png")},
            data={"source": "upload"},
        )
        assert response.status_code == 201
    return uploaded


def configured_classifier(
    furniture_type: FurnitureType = FurnitureType.BOOKSHELF,
    *,
    name: str = "test-classifier",
    version: str = "1.0",
    confidence: Decimal = Decimal("0.9375"),
) -> RecordingClassifier:
    classifier = RecordingClassifier(
        ClassificationPrediction(
            furniture_type=furniture_type,
            classifier_name=name,
            classifier_version=version,
            confidence=confidence,
        )
    )
    app.dependency_overrides[get_furniture_classifier] = lambda: classifier
    return classifier


def test_requires_all_five_views_before_calling_classifier(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory, ("front",))
    classifier = configured_classifier()

    response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Classification requires all five image views; "
            "missing: back, left, right, top"
        )
    }
    assert classifier.calls == []


def test_default_classifier_reports_unavailable_without_fake_result(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory)

    response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Furniture classifier is not configured"}
    assert db_client.get(
        f"/api/v1/furniture/{furniture_id}/classification"
    ).status_code == 404


def test_classifies_canonical_image_set_and_persists_latest_result(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    uploaded = upload_views(db_client, furniture_id, image_bytes_factory)
    classifier = configured_classifier()

    response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["predicted_type"] == "bookshelf"
    assert result["confidence"] == "0.9375"
    assert result["classifier_name"] == "test-classifier"
    assert result["classifier_version"] == "1.0"
    assert len(result["input_signature"]) == 64
    assert len(classifier.calls) == 1
    assert [image.view for image in classifier.calls[0]] == list(FurnitureImageView)
    assert {
        image.view.value: image.data for image in classifier.calls[0]
    } == uploaded

    stored = db_client.get(
        f"/api/v1/furniture/{furniture_id}/classification"
    )
    assert stored.status_code == 200
    assert stored.json() == result
    furniture = db_client.get(f"/api/v1/furniture/{furniture_id}").json()
    assert furniture["furniture_type"] == "bookshelf"


def test_reclassification_updates_one_result_in_place(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory)
    configured_classifier()
    first = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    ).json()

    configured_classifier(
        FurnitureType.DINING_TABLE,
        name="replacement-model",
        version="2.0",
        confidence=Decimal("0.8000"),
    )
    second_response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )

    assert second_response.status_code == 200
    second = second_response.json()
    assert second["id"] == first["id"]
    assert second["input_signature"] == first["input_signature"]
    assert second["predicted_type"] == "dining_table"
    assert second["classifier_name"] == "replacement-model"


def test_image_or_manual_type_change_invalidates_classification(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory)
    configured_classifier()
    classification_url = f"/api/v1/furniture/{furniture_id}/classification"
    assert db_client.post(classification_url).status_code == 200

    assert db_client.delete(
        f"/api/v1/furniture/{furniture_id}/images/top"
    ).status_code == 204
    assert db_client.get(classification_url).status_code == 404

    upload_views(db_client, furniture_id, image_bytes_factory, ("top",))
    assert db_client.post(classification_url).status_code == 200
    patch_response = db_client.patch(
        f"/api/v1/furniture/{furniture_id}",
        json={"furniture_type": "chair"},
    )
    assert patch_response.status_code == 200
    assert db_client.get(classification_url).status_code == 404


def test_unavailable_stored_view_blocks_classification(
    db_client: TestClient,
    image_storage: LocalImageStorage,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory)
    configured_classifier()
    stored_file = next(path for path in image_storage.root.rglob("*") if path.is_file())
    missing_view = stored_file.parent.name
    stored_file.unlink()

    response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Stored content is unavailable for the {missing_view} view"
    }


def test_tampered_stored_view_blocks_classification(
    db_client: TestClient,
    image_storage: LocalImageStorage,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory)
    configured_classifier()
    stored_file = next(path for path in image_storage.root.rglob("*") if path.is_file())
    tampered_view = stored_file.parent.name
    stored_file.write_bytes(b"tampered")

    response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            f"Stored content failed integrity validation for the {tampered_view} view"
        )
    }


def test_invalid_adapter_output_and_missing_furniture_are_reported(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    missing_id = uuid4()
    assert db_client.get(
        f"/api/v1/furniture/{missing_id}/classification"
    ).status_code == 404

    furniture_id = create_furniture(db_client)
    upload_views(db_client, furniture_id, image_bytes_factory)
    app.dependency_overrides[get_furniture_classifier] = lambda: InvalidObjectClassifier()
    response = db_client.post(
        f"/api/v1/furniture/{furniture_id}/classification"
    )
    assert response.status_code == 502
    assert response.json() == {
        "detail": "Classifier adapter returned an invalid prediction object"
    }
