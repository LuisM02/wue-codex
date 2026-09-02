"""PostgreSQL/filesystem tests for photo-derived part reconstruction."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_furniture_reconstructor
from app.core.enums import FurnitureImageView
from app.main import app
from app.schemas.photo_reconstruction import ReconstructionPartProposal
from app.services.photo_reconstruction import ReconstructionPrediction

pytestmark = pytest.mark.integration


class PhotoSensitiveReconstructor:
    def __init__(self) -> None:
        self.calls = []

    def reconstruct(self, images, furniture_type, dimensions):
        self.calls.append((images, furniture_type, dimensions))
        front = next(image for image in images if image.view == FurnitureImageView.FRONT)
        inset = Decimal(str(front.data[19] % 40 + 20))
        width = dimensions.width_mm - inset * 2
        return ReconstructionPrediction(
            provider_name="photo-sensitive-test-model",
            provider_version="0.1",
            confidence=Decimal("0.8125"),
            warnings=("Rear joinery is partly occluded",),
            parts=(
                ReconstructionPartProposal(
                    component_name="seat",
                    component_type="panel",
                    geometry_kind="extruded_profile",
                    profile_points=[
                        {"u": "0", "v": "0"},
                        {"u": str(width), "v": "0"},
                        {"u": str(width - inset), "v": "50"},
                        {"u": str(inset), "v": "50"},
                    ],
                    width=width,
                    height="50",
                    depth=dimensions.depth_mm - Decimal("100"),
                    x=inset,
                    y="450",
                    z="50",
                    confidence="0.91",
                    source_views=["front", "left", "right", "top"],
                ),
            ),
        )


def create_ready_furniture(
    client: TestClient,
    image_bytes_factory,
    *,
    size_offset: int = 0,
) -> tuple[str, dict[str, bytes]]:
    project = client.post("/api/v1/projects", json={"name": "Photo reconstruction"}).json()
    furniture = client.post(
        f"/api/v1/projects/{project['id']}/furniture",
        json={"name": "Actual photographed chair", "furniture_type": "chair"},
    ).json()
    furniture_id = furniture["id"]
    assert client.put(
        f"/api/v1/furniture/{furniture_id}/dimensions",
        json={"width": 800, "height": 1000, "depth": 600, "unit": "mm"},
    ).status_code == 201
    uploaded = {}
    for index, view in enumerate(FurnitureImageView):
        data = image_bytes_factory(
            "PNG", size=(10 + size_offset + index, 8 + size_offset + index)
        )
        uploaded[view.value] = data
        assert client.post(
            f"/api/v1/furniture/{furniture_id}/images/{view.value}",
            files={"file": (f"{view.value}.png", data, "image/png")},
            data={"source": "upload"},
        ).status_code == 201
    return furniture_id, uploaded


def test_default_provider_refuses_to_make_a_generic_substitute(
    db_client: TestClient,
    image_bytes_factory,
) -> None:
    furniture_id, _ = create_ready_furniture(db_client, image_bytes_factory)

    response = db_client.post(f"/api/v1/furniture/{furniture_id}/reconstruction")

    assert response.status_code == 503
    assert response.json() == {
        "detail": (
            "Photo reconstruction AI is not configured; "
            "WUE will not generate a generic substitute"
        )
    }
    plan = db_client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert plan.status_code == 409
    assert "will not use a generic furniture template" in plan.json()["detail"]


def test_provider_receives_pixels_and_plan_copies_photo_derived_profile(
    db_client: TestClient,
    image_bytes_factory,
) -> None:
    furniture_id, uploaded = create_ready_furniture(db_client, image_bytes_factory)
    provider = PhotoSensitiveReconstructor()
    app.dependency_overrides[get_furniture_reconstructor] = lambda: provider

    response = db_client.post(f"/api/v1/furniture/{furniture_id}/reconstruction")

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["provider_name"] == "photo-sensitive-test-model"
    assert result["confidence"] == "0.8125"
    assert len(result["input_signature"]) == 64
    assert result["warnings"] == ["Rear joinery is partly occluded"]
    assert len(provider.calls) == 1
    images, furniture_type, dimensions = provider.calls[0]
    assert {image.view.value: image.data for image in images} == uploaded
    assert furniture_type.value == "chair"
    assert dimensions.width_mm == Decimal("800.0000")

    source_part = result["parts"][0]
    assert source_part["geometry_kind"] == "extruded_profile"
    assert source_part["source_views"] == ["front", "left", "right", "top"]
    plan_response = db_client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert plan_response.status_code == 201, plan_response.text
    plan = plan_response.json()
    assert plan["source_reconstruction_id"] == result["id"]
    assert len(plan["components"]) == 1
    component = plan["components"][0]
    assert component["source_reconstruction_part_id"] == source_part["id"]
    assert component["profile_points"] == source_part["profile_points"]
    assert component["source_confidence"] == "0.9100"


def test_source_change_invalidates_reconstruction(
    db_client: TestClient,
    image_bytes_factory,
) -> None:
    furniture_id, _ = create_ready_furniture(db_client, image_bytes_factory)
    app.dependency_overrides[get_furniture_reconstructor] = PhotoSensitiveReconstructor
    assert db_client.post(
        f"/api/v1/furniture/{furniture_id}/reconstruction"
    ).status_code == 200

    assert db_client.delete(
        f"/api/v1/furniture/{furniture_id}/images/top"
    ).status_code == 204
    assert db_client.get(
        f"/api/v1/furniture/{furniture_id}/reconstruction"
    ).status_code == 404


def test_different_photo_pixels_produce_different_plans_at_the_same_scale(
    db_client: TestClient,
    image_bytes_factory,
) -> None:
    first_id, _ = create_ready_furniture(db_client, image_bytes_factory)
    second_id, _ = create_ready_furniture(
        db_client, image_bytes_factory, size_offset=7
    )
    app.dependency_overrides[get_furniture_reconstructor] = PhotoSensitiveReconstructor

    first_reconstruction = db_client.post(
        f"/api/v1/furniture/{first_id}/reconstruction"
    ).json()
    second_reconstruction = db_client.post(
        f"/api/v1/furniture/{second_id}/reconstruction"
    ).json()
    first_plan = db_client.post(f"/api/v1/furniture/{first_id}/plans").json()
    second_plan = db_client.post(f"/api/v1/furniture/{second_id}/plans").json()

    assert first_reconstruction["input_signature"] != second_reconstruction["input_signature"]
    assert first_plan["components"][0]["width"] != second_plan["components"][0]["width"]
    assert (
        first_plan["components"][0]["profile_points"]
        != second_plan["components"][0]["profile_points"]
    )


def test_reconstruction_reports_missing_resources_and_prerequisites(
    db_client: TestClient,
) -> None:
    assert db_client.post(
        f"/api/v1/furniture/{uuid4()}/reconstruction"
    ).status_code == 404
    project = db_client.post("/api/v1/projects", json={"name": "Incomplete"}).json()
    furniture = db_client.post(
        f"/api/v1/projects/{project['id']}/furniture",
        json={"name": "Unknown"},
    ).json()
    response = db_client.post(
        f"/api/v1/furniture/{furniture['id']}/reconstruction"
    )
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Furniture recognition is required before part reconstruction"
    }
