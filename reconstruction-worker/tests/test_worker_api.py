"""End-to-end HTTP tests for photo validation and silhouette-derived geometry."""

import hashlib
import json
from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageOps

from wue_worker.imaging import analyze_image
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


def _table_image(
    view: str, *, aprons: bool = True, side_aprons: bool | None = None,
    inset: int = 0, small_overhang: bool = False, side_apron_height: int = 20,
) -> bytes:
    image = Image.new("RGB", (280, 240), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    wood = "#68412b"
    if view in {"front", "back"}:
        draw.rounded_rectangle((25, 40, 255, 66), radius=7, fill=wood)
        if aprons:
            draw.rectangle((27, 62, 253, 82) if small_overhang else (48 + inset, 62, 232 - inset, 82), fill=wood)
        draw.polygon([(48 + inset, 62), (73 + inset, 62), (68 + inset, 218), (54 + inset, 218)], fill=wood)
        draw.polygon([(207 - inset, 62), (232 - inset, 62), (226 - inset, 218), (212 - inset, 218)], fill=wood)
    elif view in {"left", "right"}:
        draw.rounded_rectangle((55, 40, 205, 66), radius=7, fill=wood)
        if (aprons if side_aprons is None else side_aprons):
            draw.rectangle((58, 62, 202, 62 + side_apron_height) if small_overhang else (72, 62, 190, 62 + side_apron_height), fill=wood)
        draw.polygon([(72, 62), (96, 62), (91, 218), (78, 218)], fill=wood)
        draw.polygon([(166, 62), (190, 62), (184, 218), (172, 218)], fill=wood)
    else:
        draw.rounded_rectangle((20, 60, 260, 180), radius=9, fill=wood)
    marker = VIEWS.index(view) * 3
    draw.rectangle((8 + marker, 8, 9 + marker, 9), fill="#d8d5cd")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _slatted_chair_image(view: str) -> bytes:
    image = Image.new("RGB", (240, 240), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    wood = "#68412b"
    if view in {"front", "back"}:
        draw.rectangle((48, 22, 192, 42), fill=wood)
        for x in (52, 78, 104, 130, 156, 182):
            draw.rectangle((x, 38, x + 8, 112), fill=wood)
        draw.rectangle((42, 108, 198, 126), fill=wood)
        draw.polygon([(53, 122), (72, 122), (65, 220), (52, 220)], fill=wood)
        draw.polygon([(168, 122), (188, 122), (185, 220), (173, 220)], fill=wood)
    elif view in {"left", "right"}:
        draw.rectangle((150, 22, 172, 112), fill=wood)
        draw.rectangle((48, 108, 184, 126), fill=wood)
        draw.rectangle((55, 122, 72, 220), fill=wood)
        draw.rectangle((160, 122, 177, 220), fill=wood)
    else:
        draw.rounded_rectangle((45, 58, 195, 182), radius=12, fill=wood)
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


def _unsupported_image(view, shape):
    image = Image.new("RGB", (240, 260), "#f7f5ef")
    draw = ImageDraw.Draw(image)
    if shape == "disc":
        draw.ellipse((40, 40, 200, 220), fill="#68412b")
    elif shape == "box":
        draw.rectangle((40, 25, 200, 230), fill="#68412b")
    elif shape == "vase":
        draw.polygon([(95, 25), (145, 25), (140, 70), (190, 160), (165, 230),
                      (75, 230), (50, 160), (100, 70)], fill="#68412b")
    else:
        raise AssertionError(shape)
    marker = VIEWS.index(view) * 3
    draw.rectangle((8 + marker, 8, 9 + marker, 9), fill="#d8d5cd")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


@pytest.mark.parametrize("shape", ["disc", "box", "vase"])
def test_clear_unrelated_shapes_are_rejected_not_forced_into_supported_types(client, shape):
    files, manifest = _files_for(lambda view: _unsupported_image(view, shape))
    response = client.post("/v1/classify", files=files, data={"image_manifest": json.dumps(manifest)})
    assert response.status_code == 422, response.text
    assert "Unsupported or uncertain furniture" in response.json()["detail"]
    # A caller cannot evade the same evidence gate by supplying a type.
    response = client.post("/v1/reconstruct", files=files, data={
        "furniture_type": "bookshelf", "width_mm": "600", "height_mm": "1200",
        "depth_mm": "600", "image_manifest": json.dumps(manifest),
    })
    assert response.status_code == 422, response.text
    assert "Unsupported or uncertain furniture" in response.json()["detail"]


def test_incompatible_front_and_side_structure_is_rejected(client):
    files, manifest = _files_for(lambda view: _chair_image(view) if view in {"front", "back", "top"} else _table_image(view))
    response = client.post("/v1/classify", files=files, data={"image_manifest": json.dumps(manifest)})
    assert response.status_code == 422, response.text


def test_supported_structure_cannot_be_reconstructed_as_a_different_type(client):
    files, manifest = _files_for(_table_image)
    response = client.post("/v1/reconstruct", files=files, data={
        "furniture_type": "bookshelf", "width_mm": "1800", "height_mm": "750",
        "depth_mm": "900", "image_manifest": json.dumps(manifest),
    })
    assert response.status_code == 422, response.text
    assert "does not match" in response.json()["detail"]


def test_perspective_visible_extra_legs_do_not_reject_a_supported_chair(client):
    def photos(view):
        with Image.open(BytesIO(_chair_image(view))) as image:
            if view in {"front", "back"}:
                draw = ImageDraw.Draw(image)
                draw.rectangle((91, 124, 97, 205), fill="#68412b")
                draw.rectangle((143, 124, 149, 205), fill="#68412b")
            output = BytesIO()
            image.save(output, "PNG")
            return output.getvalue()
    files, manifest = _files_for(photos)
    response = client.post("/v1/classify", files=files, data={"image_manifest": json.dumps(manifest)})
    assert response.status_code == 200, response.text
    assert response.json()["furniture_type"] == "chair"
    assert response.json()["classifier_version"].endswith("+structure-gate-v1")


def test_health_and_model_status_are_honest(client: TestClient) -> None:
    assert client.get("/health").json()["version"] == "0.3.0"
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
    assert {
        "front_left_leg",
        "front_right_leg",
        "rear_left_leg",
        "rear_right_leg",
    }.issubset(names)
    assert not any(name.endswith("_support") for name in names)
    assert len(
        [part for part in body["parts"] if part["component_type"] == "leg"]
    ) == 4
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
        if furniture_type == "dining_table":
            assert {
                "front_left_leg",
                "front_right_leg",
                "rear_left_leg",
                "rear_right_leg",
                "front_apron",
                "rear_apron",
                "left_apron",
                "right_apron",
            } <= names
            table_parts = {
                part["component_name"]: part
                for part in reconstructed.json()["parts"]
            }
            assert table_parts["tabletop"]["height"] <= dimensions[1] * 0.07
            assert table_parts["front_left_leg"]["height"] >= dimensions[1] * 0.9


def test_table_without_visible_aprons_does_not_invent_panels(client: TestClient) -> None:
    files, manifest = _files_for(lambda view: _table_image(view, aprons=False))
    response = client.post(
        "/v1/reconstruct",
        files=files,
        data={
            "furniture_type": "dining_table",
            "width_mm": "1800",
            "height_mm": "750",
            "depth_mm": "900",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    names = {part["component_name"] for part in response.json()["parts"]}
    assert names == {
        "tabletop", "front_left_leg", "front_right_leg",
        "rear_left_leg", "rear_right_leg",
    }


def test_table_aprons_with_small_overhang_are_retained(client: TestClient) -> None:
    files, manifest = _files_for(lambda view: _table_image(view, small_overhang=True))
    response = client.post(
        "/v1/reconstruct",
        files=files,
        data={
            "furniture_type": "dining_table", "width_mm": "1800",
            "height_mm": "750", "depth_mm": "900",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    names = {part["component_name"] for part in response.json()["parts"]}
    assert {"front_apron", "rear_apron", "left_apron", "right_apron"} <= names


def test_side_aprons_require_side_view_evidence(client: TestClient) -> None:
    files, manifest = _files_for(lambda view: _table_image(view, side_aprons=False))
    response = client.post(
        "/v1/reconstruct",
        files=files,
        data={
            "furniture_type": "dining_table",
            "width_mm": "1800",
            "height_mm": "750",
            "depth_mm": "900",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    names = {part["component_name"] for part in response.json()["parts"]}
    assert {"front_apron", "rear_apron"} <= names
    assert "left_apron" not in names
    assert "right_apron" not in names


def test_new_table_leg_spacing_changes_geometry(client: TestClient) -> None:
    proposed = []
    for inset in (0, 22):
        files, manifest = _files_for(lambda view: _table_image(view, inset=inset))
        response = client.post(
            "/v1/reconstruct",
            files=files,
            data={
                "furniture_type": "dining_table",
                "width_mm": "1800",
                "height_mm": "750",
                "depth_mm": "900",
                "image_manifest": json.dumps(manifest),
            },
        )
        assert response.status_code == 200, response.text
        proposed.append({part["component_name"]: part for part in response.json()["parts"]})
    assert proposed[1]["front_left_leg"]["x"] > proposed[0]["front_left_leg"]["x"] + 100
    assert proposed[1]["front_right_leg"]["x"] < proposed[0]["front_right_leg"]["x"] - 100
    assert proposed[0]["tabletop"]["width"] == proposed[1]["tabletop"]["width"]


def test_side_aprons_do_not_require_a_visible_front_apron(client: TestClient) -> None:
    files, manifest = _files_for(lambda view: _table_image(view, aprons=False, side_aprons=True))
    response = client.post(
        "/v1/reconstruct", files=files,
        data={
            "furniture_type": "dining_table", "width_mm": "1800",
            "height_mm": "750", "depth_mm": "900",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    parts = {part["component_name"]: part for part in response.json()["parts"]}
    assert {"left_apron", "right_apron"} <= parts.keys()
    assert "front_apron" not in parts and "rear_apron" not in parts
    for name in ("left_apron", "right_apron"):
        assert parts[name]["height"] > 10
        assert parts[name]["y"] + parts[name]["height"] <= 750.001


def test_side_apron_height_comes_from_its_own_view(client: TestClient) -> None:
    proposals = []
    for apron_height in (12, 32):
        files, manifest = _files_for(lambda view: _table_image(view, side_apron_height=apron_height))
        response = client.post(
            "/v1/reconstruct", files=files,
            data={
                "furniture_type": "dining_table", "width_mm": "1800",
                "height_mm": "750", "depth_mm": "900",
                "image_manifest": json.dumps(manifest),
            },
        )
        assert response.status_code == 200, response.text
        proposals.append({part["component_name"]: part for part in response.json()["parts"]})
    assert proposals[1]["left_apron"]["height"] > proposals[0]["left_apron"]["height"] + 40
    assert proposals[1]["front_apron"]["height"] == proposals[0]["front_apron"]["height"]


def test_neural_box_mask_cannot_fill_open_table_space() -> None:
    class FloodedMaskProvider(BaselineSegmentationProvider):
        def refine_mask(self, view_name, image, seed_mask, seed_bbox):
            del view_name, seed_mask
            left, top, right, bottom = seed_bbox
            mask = bytearray(image.width * image.height)
            for y in range(top, bottom):
                mask[y * image.width + left : y * image.width + right] = (
                    b"\x01" * (right - left)
                )
            return bytes(mask)

    photo = _table_image("front")
    baseline = analyze_image("front", photo)
    refined = analyze_image("front", photo, FloodedMaskProvider())
    assert refined.mask == baseline.mask
    assert refined.segmentation_warning is not None


def test_expanded_neural_mask_cannot_absorb_the_floor() -> None:
    class FloorMaskProvider(BaselineSegmentationProvider):
        def refine_mask(self, view_name, image, seed_mask, bbox):
            expanded = bytearray(seed_mask)
            for y in range(160, 235):
                expanded[y * image.width + 20:y * image.width + 225] = b"\x01" * 205
            return bytes(expanded)

    photo = _chair_image("left")
    baseline = analyze_image("left", photo)
    refined = analyze_image("left", photo, FloorMaskProvider())
    assert refined.mask == baseline.mask
    assert refined.segmentation_warning is not None


def test_slatted_backrest_keeps_its_internal_parts(client: TestClient) -> None:
    files, manifest = _files_for(_slatted_chair_image)
    response = client.post(
        "/v1/reconstruct", files=files,
        data={
            "furniture_type": "chair", "width_mm": "450",
            "height_mm": "900", "depth_mm": "500",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    names = {part["component_name"] for part in response.json()["parts"]}
    assert {"left_backrest_post", "right_backrest_post"} <= names
    assert {f"backrest_slat_{index}" for index in range(1, 5)} <= names
    assert len([name for name in names if name.startswith("backrest_slat_")]) == 4
    assert len([part for part in response.json()["parts"] if part["component_type"] == "leg"]) == 4


def test_chair_backrest_uses_canonical_right_elevation_depth(client: TestClient) -> None:
    def photos(view):
        data = _chair_image(view)
        if view != "left":
            return data
        with Image.open(BytesIO(data)) as image:
            output = BytesIO()
            ImageOps.mirror(image).save(output, "PNG")
            return output.getvalue()

    files, manifest = _files_for(photos)
    response = client.post(
        "/v1/reconstruct", files=files,
        data={
            "furniture_type": "chair", "width_mm": "450",
            "height_mm": "900", "depth_mm": "500",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    backrest = next(part for part in response.json()["parts"] if part["component_name"] == "backrest")
    assert backrest["z"] > 250


def test_table_dimension_photo_conflict_is_reported(client: TestClient) -> None:
    files, manifest = _files_for(_table_image)
    response = client.post(
        "/v1/reconstruct",
        files=files,
        data={
            "furniture_type": "dining_table",
            "width_mm": "450",
            "height_mm": "900",
            "depth_mm": "500",
            "image_manifest": json.dumps(manifest),
        },
    )
    assert response.status_code == 200, response.text
    assert any(
        "width and height strongly disagree" in warning
        for warning in response.json()["warnings"]
    )


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
