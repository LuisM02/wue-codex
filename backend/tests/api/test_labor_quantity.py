"""Real PostgreSQL API tests for calculation-only labor hours."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def create_draft(client: TestClient, furniture_type: str) -> dict:
    project = client.post(
        "/api/v1/projects",
        json={"name": f"{furniture_type} labor"},
    )
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Labor source", "furniture_type": furniture_type},
    )
    furniture_id = furniture.json()["id"]
    dimensions = client.put(
        f"/api/v1/furniture/{furniture_id}/dimensions",
        json={"width": 1000, "height": 1200, "depth": 600, "unit": "mm"},
    )
    assert dimensions.status_code == 201
    response = client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert response.status_code == 201
    return response.json()


def finalize(client: TestClient, draft: dict) -> dict:
    response = client.post(f"/api/v1/plans/{draft['id']}/finalize")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    ("furniture_type", "expected_hours", "expected_rules"),
    [
        (
            "chair",
            "2.50",
            [
                "chair_base_assembly",
                "chair_leg_work",
                "chair_backrest_work",
            ],
        ),
        (
            "dining_table",
            "3.20",
            [
                "dining_table_base_assembly",
                "dining_table_leg_work",
                "dining_table_tabletop_work",
            ],
        ),
        (
            "bookshelf",
            "3.35",
            [
                "bookshelf_base_assembly",
                "bookshelf_carcass_panel_work",
                "bookshelf_shelf_work",
            ],
        ),
    ],
)
def test_default_labor_hours_and_rule_order(
    db_client: TestClient,
    furniture_type: str,
    expected_hours: str,
    expected_rules: list[str],
) -> None:
    finalized = finalize(db_client, create_draft(db_client, furniture_type))

    response = db_client.get(
        f"/api/v1/plans/{finalized['id']}/labor-quantity"
    )

    assert response.status_code == 200
    result = response.json()
    assert result["plan_id"] == finalized["id"]
    assert result["furniture_id"] == finalized["furniture_id"]
    assert result["furniture_type"] == furniture_type
    assert result["unit"] == "hour"
    assert result["rule_set"] == "WUE v1 labor-hour estimation assumptions"
    assert Decimal(result["labor_hours"]) == Decimal(expected_hours)
    assert [item["rule_code"] for item in result["rules"]] == expected_rules
    assert sum(
        (Decimal(item["labor_hours"]) for item in result["rules"]),
        start=Decimal("0"),
    ) == Decimal(result["labor_hours"])


def test_edited_valid_design_recalculates_labor_hours(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client, "chair")
    add = db_client.post(
        f"/api/v1/plans/{draft['id']}/components",
        json={
            "component_name": "extra_leg",
            "component_type": "leg",
            "width": 50,
            "height": 500,
        },
    )
    assert add.status_code == 201
    finalized = finalize(db_client, draft)

    result = db_client.get(
        f"/api/v1/plans/{finalized['id']}/labor-quantity"
    ).json()

    assert Decimal(result["labor_hours"]) == Decimal("2.75")
    assert result["rules"][1]["unit_count"] == 5


def test_estimation_requires_finalization_but_not_3d_depth(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client, "chair")
    quantity_url = f"/api/v1/plans/{draft['id']}/labor-quantity"
    draft_response = db_client.get(quantity_url)
    assert draft_response.status_code == 409
    assert draft_response.json() == {
        "detail": "Labor quantity estimation requires a finalized 2D plan"
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
        f"/api/v1/plans/{finalized['id']}/labor-quantity"
    )
    assert response.status_code == 200
    assert Decimal(response.json()["labor_hours"]) == Decimal("2.50")


def test_estimation_is_repeatable_read_only_and_reports_missing_plan(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client, "bookshelf"))
    plan_url = f"/api/v1/plans/{finalized['id']}"
    quantity_url = f"{plan_url}/labor-quantity"
    before = db_client.get(plan_url).json()

    first = db_client.get(quantity_url)
    second = db_client.get(quantity_url)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before
    assert db_client.get(
        f"/api/v1/plans/{uuid4()}/labor-quantity"
    ).status_code == 404
