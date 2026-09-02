"""Real PostgreSQL API tests for calculation-only material quantity."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.support.photo_reconstruction import prepare_test_reconstruction

pytestmark = pytest.mark.integration


def create_draft(client: TestClient) -> dict:
    project = client.post("/api/v1/projects", json={"name": "Quantity"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Volume source", "furniture_type": "chair"},
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


def test_calculates_default_chair_volume_and_component_breakdown(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))

    response = db_client.get(
        f"/api/v1/plans/{finalized['id']}/material-quantity"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["plan_id"] == finalized["id"]
    assert result["unit"] == "mm3"
    assert result["total_volume_mm3"] == "38476800.000000000000"
    seat = next(
        item for item in result["components"] if item["component_name"] == "seat"
    )
    assert seat == {
        "source_component_id": next(
            item["id"]
            for item in finalized["components"]
            if item["component_name"] == "seat"
        ),
        "component_name": "seat",
        "component_type": "panel",
        "width_mm": "800.0000",
        "height_mm": "48.0000",
        "depth_mm": "480.0000",
        "depth_source": "component_depth",
        "quantity": 1,
        "single_piece_volume_mm3": "18432000.000000000000",
        "total_volume_mm3": "18432000.000000000000",
        "sort_order": 0,
    }


def test_quantity_multiplies_component_count_and_uses_thickness_fallback(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    patch = db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{seat['id']}",
        json={"depth": None, "thickness": "25", "quantity": 2},
    )
    assert patch.status_code == 200
    finalized = finalize(db_client, draft)

    result = db_client.get(
        f"/api/v1/plans/{finalized['id']}/material-quantity"
    ).json()
    rendered_seat = next(
        item for item in result["components"] if item["component_name"] == "seat"
    )
    assert rendered_seat["depth_mm"] == "25.0000"
    assert rendered_seat["depth_source"] == "thickness"
    assert rendered_seat["quantity"] == 2
    assert rendered_seat["single_piece_volume_mm3"] == "960000.000000000000"
    assert rendered_seat["total_volume_mm3"] == "1920000.000000000000"


def test_quantity_requires_finalized_plan_and_complete_depth(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    quantity_url = f"/api/v1/plans/{draft['id']}/material-quantity"
    assert db_client.get(quantity_url).status_code == 409
    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    assert db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{seat['id']}",
        json={"depth": None, "thickness": None},
    ).status_code == 200
    finalize(db_client, draft)

    missing_depth = db_client.get(quantity_url)

    assert missing_depth.status_code == 409
    assert "neither depth nor thickness: seat" in missing_depth.json()["detail"]


def test_quantity_is_repeatable_read_only_and_reports_missing_plan(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    plan_url = f"/api/v1/plans/{finalized['id']}"
    before = db_client.get(plan_url).json()

    first = db_client.get(f"{plan_url}/material-quantity")
    second = db_client.get(f"{plan_url}/material-quantity")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before
    assert db_client.get(
        f"/api/v1/plans/{uuid4()}/material-quantity"
    ).status_code == 404
