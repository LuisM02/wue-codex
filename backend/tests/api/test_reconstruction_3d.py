"""Real PostgreSQL API tests for deterministic 3D reconstruction."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.support.photo_reconstruction import prepare_test_reconstruction

pytestmark = pytest.mark.integration


def create_draft(client: TestClient, furniture_type: str = "chair") -> dict:
    project = client.post("/api/v1/projects", json={"name": "3D reconstruction"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Render source", "furniture_type": furniture_type},
    )
    furniture_id = furniture.json()["id"]
    dimensions = client.put(
        f"/api/v1/furniture/{furniture_id}/dimensions",
        json={"width": 1000, "height": 1200, "depth": 600, "unit": "mm"},
    )
    assert dimensions.status_code == 201
    prepare_test_reconstruction(client, furniture_id)
    response = client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert response.status_code == 201
    return response.json()


def finalize(client: TestClient, draft: dict) -> dict:
    response = client.post(f"/api/v1/plans/{draft['id']}/finalize")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("furniture_type", ["chair", "dining_table", "bookshelf"])
def test_reconstructs_every_finalized_default_in_component_order(
    db_client: TestClient,
    furniture_type: str,
) -> None:
    finalized = finalize(db_client, create_draft(db_client, furniture_type))

    response = db_client.get(
        f"/api/v1/plans/{finalized['id']}/geometry-3d"
    )

    assert response.status_code == 200
    geometry = response.json()
    assert geometry["plan_id"] == finalized["id"]
    assert geometry["furniture_id"] == finalized["furniture_id"]
    assert geometry["revision"] == 1
    assert geometry["furniture_type"] == furniture_type
    assert geometry["unit"] == "mm"
    assert [item["component_name"] for item in geometry["components"]] == [
        item["component_name"] for item in finalized["components"]
    ]
    assert all(
        item["depth_source"] == "component_depth"
        for item in geometry["components"]
    )


def test_uses_exact_decimal_center_and_preserves_render_metadata(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    patch = db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{seat['id']}",
        json={
            "width": "101.0001",
            "depth": "11.0001",
            "thickness": "99",
            "x": "-10",
            "z": "-5",
            "rotation": "45.5",
            "quantity": 3,
        },
    )
    assert patch.status_code == 200
    finalized = finalize(db_client, draft)

    geometry = db_client.get(
        f"/api/v1/plans/{finalized['id']}/geometry-3d"
    ).json()
    rendered_seat = next(
        item
        for item in geometry["components"]
        if item["component_name"] == "seat"
    )

    assert rendered_seat["dimensions"] == {
        "width": "101.0001",
        "height": "48.0000",
        "depth": "11.0001",
    }
    assert rendered_seat["min_corner"] == {
        "x": "-10.0000",
        "y": "540.0000",
        "z": "-5.0000",
    }
    assert rendered_seat["center"] == {
        "x": "40.50005",
        "y": "564.0000",
        "z": "0.50005",
    }
    assert rendered_seat["depth_source"] == "component_depth"
    assert rendered_seat["rotation_degrees"] == "45.5000"
    assert rendered_seat["quantity"] == 3


def test_uses_thickness_only_as_depth_fallback(db_client: TestClient) -> None:
    draft = create_draft(db_client)
    backrest = next(
        item
        for item in draft["components"]
        if item["component_name"] == "backrest"
    )
    patch = db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{backrest['id']}",
        json={"depth": None, "thickness": "18.5"},
    )
    assert patch.status_code == 200
    finalized = finalize(db_client, draft)

    geometry = db_client.get(
        f"/api/v1/plans/{finalized['id']}/geometry-3d"
    ).json()
    rendered = next(
        item
        for item in geometry["components"]
        if item["component_name"] == "backrest"
    )
    assert rendered["dimensions"]["depth"] == "18.5000"
    assert rendered["depth_source"] == "thickness"


def test_missing_depth_and_thickness_fail_after_valid_finalization(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    patch = db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{seat['id']}",
        json={"depth": None, "thickness": None},
    )
    assert patch.status_code == 200
    finalized = finalize(db_client, draft)

    response = db_client.get(
        f"/api/v1/plans/{finalized['id']}/geometry-3d"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "3D depth is unavailable because these components have neither "
            "depth nor thickness: seat"
        )
    }


def test_reconstruction_requires_finalized_plan(db_client: TestClient) -> None:
    draft = create_draft(db_client)

    response = db_client.get(f"/api/v1/plans/{draft['id']}/geometry-3d")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "3D reconstruction requires a finalized 2D plan"
    }


def test_reconstruction_is_repeatable_and_read_only(db_client: TestClient) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    plan_url = f"/api/v1/plans/{finalized['id']}"
    before = db_client.get(plan_url).json()

    first = db_client.get(f"{plan_url}/geometry-3d")
    second = db_client.get(f"{plan_url}/geometry-3d")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before


def test_reconstruction_reports_missing_plan(db_client: TestClient) -> None:
    response = db_client.get(f"/api/v1/plans/{uuid4()}/geometry-3d")

    assert response.status_code == 404
    assert response.json() == {"detail": "Plan not found"}
