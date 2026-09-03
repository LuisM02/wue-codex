"""End-to-end HTTP tests for photo validation and silhouette-derived geometry."""

import hashlib
import json
from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from wue_worker.main import app
from wue_worker.segmentation import (
    BaselineSegmentationProvider,
    SegmentationStatus,
    get_segmentation_provider,
)

VIEWS = ("front", "back", "left", "right", "top")


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        test_client.close()


class FakeNeuralSegmentation(BaselineSegmentationProvider):
    provider_name = "test-sam2-segmenter"
    provider_version = "test-checkpoint"
    classifier_name = "test-classifier+sam2"
    reconstruction_warning = "Test neural outline; dense depth is not loaded"

    @property
    def status(self) -> SegmentationStatus:
        return SegmentationStatus(
            ready=True,
            pipeline="test-sam2-pipeline",
            uses_gpu=True,
            loaded_checkpoints=("test-sam2.pt",),
            limitations=("Dense depth is not loaded",),
        )


def _chair_image(view: str, *, variant: int = 0) -> bytes:
    image = Image.new("RGB", (240, 240), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    wood = "#5d3826" if view != "back" else "#68412b"
    if view in {"front", "back"}:
        left = 66 - variant * 5
        right = 174 + variant * 5
        draw.rounded_rectangle((left, 25, right, 110), radius=14 + variant, fill=wood)
        draw.polygon(
            [(52, 105), (188, 105), (180 - variant * 4, 127), (60 + variant * 4, 127)],
            fill=wood,
        )
        draw.polygon([(63, 123), (86, 123), (82 + variant * 3, 220), (68, 220)], fill=wood)
        draw.polygon([(154, 123), (177, 123), (172, 220), (158 - variant * 3, 220)], fill=wood)
    elif view in {"left", "right"}:
        draw.rounded_rectangle((146, 25, 171, 113), radius=8, fill=wood)
        draw.polygon([(54, 105), (178, 105), (170, 128), (61, 128)], fill=wood)
        draw.polygon([(62, 124), (83, 124), (78, 220), (68, 220)], fill=wood)
        draw.polygon([(148, 124), (169, 124), (174, 220), (158, 220)], fill=wood)
    else:
        draw.rounded_rectangle((45, 58, 195, 182), radius=12 + variant, fill=wood)
    view_marker = VIEWS.index(view) * 3
    draw.rectangle(
        (8 + variant + view_marker, 8, 9 + variant + view_marker, 9),
        fill="#d8d5cd",
    )
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _table_image(view: str) -> bytes:
    image = Image.new("RGB", (280, 240), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    wood = "#68412b"
    if view in {"front", "back"}:
        draw.rounded_rectangle((25, 40, 255, 66), radius=7, fill=wood)
        draw.polygon([(48, 62), (73, 62), (68, 218), (54, 218)], fill=wood)
        draw.polygon([(207, 62), (232, 62), (226, 218), (212, 218)], fill=wood)
    elif view in {"left", "right"}:
        draw.rounded_rectangle((55, 40, 205, 66), radius=7, fill=wood)
        draw.polygon([(72, 62), (96, 62), (91, 218), (78, 218)], fill=wood)
        draw.polygon([(166, 62), (190, 62), (184, 218), (172, 218)], fill=wood)
    else:
        draw.rounded_rectangle((20, 60, 260, 180), radius=9, fill=wood)
    marker = VIEWS.index(view) * 3
    draw.rectangle((8 + marker, 8, 9 + marker, 9), fill="#d8d5cd")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _bookshelf_image(view: str) -> bytes:
    image = Image.new("RGB", (280, 260), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    wood = "#68412b"
    if view in {"front", "back"}:
        draw.rectangle((30, 20, 52, 235), fill=wood)
        draw.rectangle((228, 20, 250, 235), fill=wood)
        for y in (20, 72, 124, 176, 220):
            draw.rounded_rectangle((30, y, 250, y + 15), radius=3, fill=wood)
    elif view in {"left", "right"}:
        draw.rectangle((70, 20, 92, 235), fill=wood)
        draw.rectangle((188, 20, 210, 235), fill=wood)
        for y in (20, 72, 124, 176, 220):
            draw.rectangle((70, y, 210, y + 15), fill=wood)
    else:
        draw.rounded_rectangle((25, 75, 255, 175), radius=4, fill=wood)
    marker = VIEWS.index(view) * 3
    draw.rectangle((8 + marker, 8, 9 + marker, 9), fill="#d8d5cd")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _payload(*, variant: int = 0) -> tuple[dict, list[dict[str, str]]]:
    data_by_view = {
        view: _chair_image(view, variant=variant) for view in VIEWS
    }
    files = {
        view: (f"{view}.png", data, "image/png")
        for view, data in data_by_view.items()
    }
    manifest = [
        {"view": view, "checksum_sha256": hashlib.sha256(data).hexdigest()}
        for view, data in data_by_view.items()
    ]
    return files, manifest


def _files_for(factory) -> tuple[dict, list[dict[str, str]]]:
    data_by_view = {view: factory(view) for view in VIEWS}
    files = {
        view: (f"{view}.png", data, "image/png")
        for view, data in data_by_view.items()
    }
    manifest = [
        {"view": view, "checksum_sha256": hashlib.sha256(data).hexdigest()}
        for view, data in data_by_view.items()
    ]
    return files, manifest


def test_health_and_model_status_are_honest(client: TestClient) -> None:
    assert client.get("/health").json()["version"] == "0.2.0"
    status = client.get("/v1/model-status").json()
    assert status["ready"] is True
    assert status["uses_gpu"] is False
    assert status["loaded_checkpoints"] == []
    assert "silhouette" in status["pipeline"]


def test_selected_segmenter_drives_status_and_provenance(
    client: TestClient,
) -> None:
    app.dependency_overrides[get_segmentation_provider] = FakeNeuralSegmentation

    status = client.get("/v1/model-status").json()
    assert status == {
        "ready": True,
        "pipeline": "test-sam2-pipeline",
        "uses_gpu": True,
        "loaded_checkpoints": ["test-sam2.pt"],
        "limitations": ["Dense depth is not loaded"],
    }

    files, manifest = _payload()
    response = client.post(
        "/v1/reconstruct",
        files=files,
        data={
            "furniture_type": "chair",
            "width_mm": "520",
            "height_mm": "900",
            "depth_mm": "560",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider_name"] == "test-sam2-segmenter"
    assert body["provider_version"] == "test-checkpoint"
    assert body["warnings"][0] == "Test neural outline; dense depth is not loaded"


def test_sam2_configuration_without_checkpoint_refuses_inference(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WUE_WORKER_SEGMENTATION_PROVIDER", "sam2")
    monkeypatch.delenv("WUE_SAM2_CHECKPOINT", raising=False)
    get_segmentation_provider.cache_clear()
    try:
        status = client.get("/v1/model-status").json()
        assert status["ready"] is False
        assert status["loaded_checkpoints"] == []
        assert "WUE_SAM2_CHECKPOINT" in status["limitations"][0]

        files, manifest = _payload()
        response = client.post(
            "/v1/classify",
            files=files,
            data={"image_manifest": json.dumps(manifest)},
        )
        assert response.status_code == 503
        assert "configured but unavailable" in response.json()["detail"]
    finally:
        get_segmentation_provider.cache_clear()


def test_worker_classifies_and_reconstructs_a_photo_derived_chair(
    client: TestClient,
) -> None:
    files, manifest = _payload()
    response = client.post(
        "/v1/classify",
        files=files,
        data={"image_manifest": json.dumps(manifest)},
    )
    assert response.status_code == 200, response.text
    assert response.json()["furniture_type"] == "chair"

    files, manifest = _payload()
    response = client.post(
        "/v1/reconstruct",
        files=files,
        data={
            "furniture_type": "chair",
            "width_mm": "520",
            "height_mm": "900",
            "depth_mm": "560",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    names = [part["component_name"] for part in body["parts"]]
    assert names[:2] == ["seat", "backrest"]
    assert any(part["component_type"] == "leg" for part in body["parts"])
    assert all(part["geometry_kind"] == "extruded_profile" for part in body["parts"])
    assert all(len(part["profile_points"]) >= 3 for part in body["parts"])
    assert "does not yet run SAM 2" in body["warnings"][0]


def test_visibly_different_chair_changes_the_traced_geometry(
    client: TestClient,
) -> None:
    results = []
    for variant in (0, 1):
        files, manifest = _payload(variant=variant)
        response = client.post(
            "/v1/reconstruct",
            files=files,
            data={
                "furniture_type": "chair",
                "width_mm": "520",
                "height_mm": "900",
                "depth_mm": "560",
                "image_manifest": json.dumps(manifest),
            },
        )
        assert response.status_code == 200, response.text
        results.append(response.json())
    first_back = next(part for part in results[0]["parts"] if part["component_name"] == "backrest")
    second_back = next(part for part in results[1]["parts"] if part["component_name"] == "backrest")
    assert first_back["profile_points"] != second_back["profile_points"]


def test_table_and_bookshelf_use_their_observed_structural_bands(
    client: TestClient,
) -> None:
    cases = (
        (_table_image, "dining_table", (1800, 750, 900), "tabletop"),
        (_bookshelf_image, "bookshelf", (900, 1800, 350), "shelf_1"),
    )
    for factory, furniture_type, dimensions, required_part in cases:
        files, manifest = _files_for(factory)
        classified = client.post(
            "/v1/classify",
            files=files,
            data={"image_manifest": json.dumps(manifest)},
        )
        assert classified.status_code == 200, classified.text
        assert classified.json()["furniture_type"] == furniture_type

        files, manifest = _files_for(factory)
        reconstructed = client.post(
            "/v1/reconstruct",
            files=files,
            data={
                "furniture_type": furniture_type,
                "width_mm": str(dimensions[0]),
                "height_mm": str(dimensions[1]),
                "depth_mm": str(dimensions[2]),
                "image_manifest": json.dumps(manifest),
            },
        )
        assert reconstructed.status_code == 200, reconstructed.text
        names = {
            part["component_name"] for part in reconstructed.json()["parts"]
        }
        assert required_part in names


def test_duplicate_views_and_blank_images_are_rejected(client: TestClient) -> None:
    duplicate = _chair_image("front")
    files = {
        view: (f"{view}.png", duplicate, "image/png") for view in VIEWS
    }
    checksum = hashlib.sha256(duplicate).hexdigest()
    manifest = [
        {"view": view, "checksum_sha256": checksum} for view in VIEWS
    ]
    response = client.post(
        "/v1/classify",
        files=files,
        data={"image_manifest": json.dumps(manifest)},
    )
    assert response.status_code == 422
    assert "different photograph" in response.json()["detail"]

    blank = BytesIO()
    Image.new("RGB", (160, 160), "white").save(blank, "PNG")
    blank_bytes = blank.getvalue()
    files = {
        view: (f"{view}.png", blank_bytes + bytes([index]), "image/png")
        for index, view in enumerate(VIEWS)
    }
    manifest = [
        {
            "view": view,
            "checksum_sha256": hashlib.sha256(files[view][1]).hexdigest(),
        }
        for view in VIEWS
    ]
    response = client.post(
        "/v1/classify",
        files=files,
        data={"image_manifest": json.dumps(manifest)},
    )
    assert response.status_code == 422
