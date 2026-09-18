"""Real PostgreSQL API tests for calculation-only hardware quantity."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.support.photo_reconstruction import prepare_test_reconstruction

pytestmark = pytest.mark.integration


def create_draft(client: TestClient, furniture_type: str) -> dict:
    project = client.post(
        "/api/v1/projects",
        json={"name": f"{furniture_type} hardware"},
    )
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Hardware source", "furniture_type": furniture_type},
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
    review = client.post(f"/api/v1/plans/{draft['id']}/review-parts")
    assert review.status_code == 200
    response = client.post(f"/api/v1/plans/{draft['id']}/finalize")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    ("furniture_type", "expected_connections", "expected_quantity"),
    [
        (
            "chair",
            [
                ("leg_connections", 4, 8),
                ("backrest_connections", 1, 2),
            ],
            10,
        ),
        ("dining_table", [("leg_connections", 4, 8)], 8),
        (
            "bookshelf",
            [
                ("carcass_connections", 4, 8),
                ("shelf_connections", 6, 12),
            ],
            20,
        ),
    ],
)
def test_default_hardware_rules_for_each_furniture_type(
    db_client: TestClient,
    furniture_type: str,
    expected_connections: list[tuple[str, int, int]],
    expected_quantity: int,
) -> None:
    finalized = finalize(db_client, create_draft(db_client, furniture_type))

    response = db_client.get(
        f"/api/v1/plans/{finalized['id']}/hardware-quantity"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["plan_id"] == finalized["id"]
    assert result["furniture_type"] == furniture_type
    assert result["item_code"] == "wood_screw"
    assert result["item_name"] == "Wood screw"
    assert result["category"] == "hardware"
    assert result["unit"] == "piece"
    assert result["rule_name"] == "WUE v1 wood-screw connection rule"
    assert result["screws_per_connection"] == 2
    assert [
        (
            item["connection_type"],
            item["connection_count"],
            item["screw_quantity"],
        )
        for item in result["connections"]
    ] == expected_connections
    assert result["total_quantity"] == expected_quantity


def test_component_quantity_counts_physical_repeated_legs(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client, "chair")
    leg = next(
        item for item in draft["components"] if item["component_type"] == "leg"
    )
    patch = db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{leg['id']}",
        json={"quantity": 3},
    )
    assert patch.status_code == 200
    finalized = finalize(db_client, draft)

    result = db_client.get(
        f"/api/v1/plans/{finalized['id']}/hardware-quantity"
    ).json()

    assert result["connections"][0]["connection_count"] == 6
    assert result["total_connections"] == 7
    assert result["total_quantity"] == 14


def test_estimation_requires_finalization_but_not_3d_depth(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client, "chair")
    quantity_url = f"/api/v1/plans/{draft['id']}/hardware-quantity"
    draft_response = db_client.get(quantity_url)
    assert draft_response.status_code == 409
    assert draft_response.json() == {
        "detail": "Hardware quantity estimation requires a finalized 2D plan"
    }

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
        f"/api/v1/plans/{finalized['id']}/hardware-quantity"
    )
    assert response.status_code == 200
    assert response.json()["total_quantity"] == 10


def test_estimation_is_repeatable_read_only_and_reports_missing_plan(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client, "dining_table"))
    plan_url = f"/api/v1/plans/{finalized['id']}"
    quantity_url = f"{plan_url}/hardware-quantity"
    before = db_client.get(plan_url).json()

    first = db_client.get(quantity_url)
    second = db_client.get(quantity_url)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before
    assert db_client.get(
        f"/api/v1/plans/{uuid4()}/hardware-quantity"
    ).status_code == 404
