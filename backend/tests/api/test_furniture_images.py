"""Real PostgreSQL and filesystem tests for the five-view image API."""

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.services.image_storage import LocalImageStorage

pytestmark = pytest.mark.integration


def create_furniture(client: TestClient) -> tuple[str, str]:
    project_response = client.post("/api/v1/projects", json={"name": "Image project"})
    project_id = project_response.json()["id"]
    furniture_response = client.post(
        f"/api/v1/projects/{project_id}/furniture",
        json={"name": "Image chair", "furniture_type": "chair"},
    )
    return project_id, furniture_response.json()["id"]


def upload_image(
    client: TestClient,
    furniture_id: str,
    view: str,
    data: bytes,
    *,
    filename: str = "image.png",
    content_type: str = "image/png",
    source: str = "upload",
):
    return client.post(
        f"/api/v1/furniture/{furniture_id}/images/{view}",
        files={"file": (filename, data, content_type)},
        data={"source": source},
    )


def stored_files(storage: LocalImageStorage) -> list[Path]:
    if not storage.root.exists():
        return []
    return [path for path in storage.root.rglob("*") if path.is_file()]


def test_uploads_lists_and_downloads_all_five_views_in_canonical_order(
    db_client: TestClient,
    image_storage: LocalImageStorage,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    _, furniture_id = create_furniture(db_client)
    inputs = [
        ("top", "WEBP", "image/webp", "top.webp"),
        ("right", "JPEG", "image/jpeg", "right.jpg"),
        ("front", "PNG", "image/png", "front.png"),
        ("left", "PNG", "image/png", "left.png"),
        ("back", "JPEG", "image/jpeg", "back.jpg"),
    ]
    uploaded: dict[str, bytes] = {}

    for view, image_format, content_type, filename in inputs:
        data = image_bytes_factory(image_format)
        uploaded[view] = data
        response = upload_image(
            db_client,
            furniture_id,
            view,
            data,
            filename=filename,
            content_type=content_type,
            source="camera_capture" if view == "front" else "upload",
        )
        assert response.status_code == 201
        assert response.json()["view"] == view
        assert response.json()["source"] == (
            "camera_capture" if view == "front" else "upload"
        )
        assert response.json()["pixel_width"] == 4
        assert response.json()["pixel_height"] == 3

    list_response = db_client.get(f"/api/v1/furniture/{furniture_id}/images")
    assert list_response.status_code == 200
    assert [item["view"] for item in list_response.json()] == [
        "front",
        "back",
        "left",
        "right",
        "top",
    ]
    assert len(stored_files(image_storage)) == 5

    content_response = db_client.get(
        f"/api/v1/furniture/{furniture_id}/images/front/content"
    )
    assert content_response.status_code == 200
    assert content_response.content == uploaded["front"]
    assert content_response.headers["content-type"] == "image/png"
    assert content_response.headers["etag"]


def test_duplicate_view_conflicts_until_existing_image_is_deleted(
    db_client: TestClient,
    image_storage: LocalImageStorage,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    _, furniture_id = create_furniture(db_client)
    data = image_bytes_factory("PNG")
    assert upload_image(db_client, furniture_id, "front", data).status_code == 201

    duplicate = upload_image(db_client, furniture_id, "front", data)
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Furniture image view already exists"}

    delete_response = db_client.delete(
        f"/api/v1/furniture/{furniture_id}/images/front"
    )
    assert delete_response.status_code == 204
    assert stored_files(image_storage) == []
    assert upload_image(db_client, furniture_id, "front", data).status_code == 201


def test_updates_and_validates_persistent_photo_calibration(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    _, furniture_id = create_furniture(db_client)
    uploaded = upload_image(
        db_client,
        furniture_id,
        "left",
        image_bytes_factory("PNG"),
    )
    assert uploaded.status_code == 201
    assert {key: uploaded.json()[key] for key in (
        "object_left_ratio", "object_top_ratio", "object_width_ratio",
        "object_height_ratio", "is_mirrored",
    )} == {
        "object_left_ratio": "0.000000",
        "object_top_ratio": "0.000000",
        "object_width_ratio": "1.000000",
        "object_height_ratio": "1.000000",
        "is_mirrored": False,
    }

    payload = {
        "object_left_ratio": "0.125000",
        "object_top_ratio": "0.100000",
        "object_width_ratio": "0.750000",
        "object_height_ratio": "0.800000",
        "is_mirrored": True,
    }
    response = db_client.put(
        f"/api/v1/furniture/{furniture_id}/images/left/calibration",
        json=payload,
    )
    assert response.status_code == 200
    assert {key: response.json()[key] for key in payload} == payload

    persisted = db_client.get(
        f"/api/v1/furniture/{furniture_id}/images/left"
    )
    assert {key: persisted.json()[key] for key in payload} == payload

    invalid = db_client.put(
        f"/api/v1/furniture/{furniture_id}/images/left/calibration",
        json={**payload, "object_left_ratio": "0.500000", "object_width_ratio": "0.750000"},
    )
    assert invalid.status_code == 422


def test_calibration_requires_an_existing_furniture_image(
    db_client: TestClient,
) -> None:
    _, furniture_id = create_furniture(db_client)
    response = db_client.put(
        f"/api/v1/furniture/{furniture_id}/images/top/calibration",
        json={
            "object_left_ratio": 0,
            "object_top_ratio": 0,
            "object_width_ratio": 1,
            "object_height_ratio": 1,
            "is_mirrored": False,
        },
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Furniture image not found"}


@pytest.mark.parametrize(
    ("data", "content_type", "expected_status"),
    [
        (b"not-an-image", "image/png", 422),
        (b"GIF89a", "image/gif", 422),
    ],
)
def test_rejects_invalid_or_unsupported_image_content(
    db_client: TestClient,
    data: bytes,
    content_type: str,
    expected_status: int,
) -> None:
    _, furniture_id = create_furniture(db_client)

    response = upload_image(
        db_client,
        furniture_id,
        "front",
        data,
        content_type=content_type,
    )

    assert response.status_code == expected_status


def test_rejects_mime_spoofing_and_oversized_uploads(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    _, furniture_id = create_furniture(db_client)
    png_data = image_bytes_factory("PNG")

    mismatch = upload_image(
        db_client,
        furniture_id,
        "front",
        png_data,
        filename="fake.jpg",
        content_type="image/jpeg",
    )
    assert mismatch.status_code == 422
    assert "does not match" in mismatch.json()["detail"]

    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        max_image_bytes=5,
    )
    oversized = upload_image(
        db_client,
        furniture_id,
        "back",
        png_data,
    )
    assert oversized.status_code == 413


def test_missing_resources_and_invalid_view_are_reported(
    db_client: TestClient,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    missing_furniture_id = uuid4()
    missing_response = upload_image(
        db_client,
        str(missing_furniture_id),
        "front",
        image_bytes_factory("PNG"),
    )
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Furniture not found"}

    _, furniture_id = create_furniture(db_client)
    assert db_client.get(
        f"/api/v1/furniture/{furniture_id}/images/front"
    ).status_code == 404
    assert upload_image(
        db_client,
        furniture_id,
        "bottom",
        image_bytes_factory("PNG"),
    ).status_code == 422
    assert upload_image(
        db_client,
        furniture_id,
        "front",
        image_bytes_factory("PNG"),
        source="ai_generated",
    ).status_code == 422


def test_missing_stored_content_is_a_genuine_not_found(
    db_client: TestClient,
    image_storage: LocalImageStorage,
    image_bytes_factory: Callable[..., bytes],
) -> None:
    _, furniture_id = create_furniture(db_client)
    assert upload_image(
        db_client,
        furniture_id,
        "front",
        image_bytes_factory("PNG"),
    ).status_code == 201
    stored_files(image_storage)[0].unlink()

    response = db_client.get(
        f"/api/v1/furniture/{furniture_id}/images/front/content"
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Furniture image content not found"}


@pytest.mark.parametrize("delete_scope", ["furniture", "project"])
def test_parent_deletion_removes_database_metadata_and_stored_content(
    db_client: TestClient,
    image_storage: LocalImageStorage,
    image_bytes_factory: Callable[..., bytes],
    delete_scope: str,
) -> None:
    project_id, furniture_id = create_furniture(db_client)
    assert upload_image(
        db_client,
        furniture_id,
        "front",
        image_bytes_factory("PNG"),
    ).status_code == 201
    assert len(stored_files(image_storage)) == 1

    resource_path = (
        f"/api/v1/furniture/{furniture_id}"
        if delete_scope == "furniture"
        else f"/api/v1/projects/{project_id}"
    )
    assert db_client.delete(resource_path).status_code == 204
    assert stored_files(image_storage) == []
    assert db_client.get(
        f"/api/v1/furniture/{furniture_id}/images"
    ).status_code == 404
