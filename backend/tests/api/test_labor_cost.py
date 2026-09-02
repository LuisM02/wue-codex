"""Real PostgreSQL API tests for read-only labor cost calculation."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.support.photo_reconstruction import prepare_test_reconstruction

pytestmark = pytest.mark.integration


def create_draft(client: TestClient) -> dict:
    project = client.post("/api/v1/projects", json={"name": "Labor cost"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Cost source", "furniture_type": "chair"},
    )
    furniture_id = furniture.json()["id"]
    assert client.put(
        f"/api/v1/furniture/{furniture_id}/dimensions",
        json={"width": 1000, "height": 1200, "depth": 600, "unit": "mm"},
    ).status_code == 201
    prepare_test_reconstruction(client, furniture_id)
    response = client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert response.status_code == 201
    return response.json()


def finalize(client: TestClient, draft: dict) -> dict:
    response = client.post(f"/api/v1/plans/{draft['id']}/finalize")
    assert response.status_code == 200
    return response.json()


def create_rate(
    client: TestClient,
    *,
    name: str = "Standard woodworking",
    is_active: bool = True,
) -> dict:
    response = client.post(
        "/api/v1/admin/labor-rates",
        json={"rate_name": name, "is_active": is_active},
    )
    assert response.status_code == 201
    return response.json()


def add_price(
    client: TestClient,
    labor_rate_id: str,
    *,
    value: str,
    effective_date: str,
) -> dict:
    response = client.post(
        f"/api/v1/admin/labor-rates/{labor_rate_id}/prices",
        json={"rate_per_hour": value, "effective_date": effective_date},
    )
    assert response.status_code == 201
    return response.json()


def cost_url(plan_id: str, labor_rate_id: str) -> str:
    return f"/api/v1/plans/{plan_id}/labor-cost?labor_rate_id={labor_rate_id}"


def test_uses_future_latest_rate_and_returns_live_rule_breakdown(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    labor_rate = create_rate(db_client)
    add_price(
        db_client,
        labor_rate["id"],
        value="100",
        effective_date="2020-01-01",
    )
    future = add_price(
        db_client,
        labor_rate["id"],
        value="123.456789",
        effective_date="2099-01-01",
    )

    response = db_client.get(cost_url(finalized["id"], labor_rate["id"]))

    assert response.status_code == 200
    result = response.json()
    assert result["plan_id"] == finalized["id"]
    assert result["labor_rate_id"] == labor_rate["id"]
    assert result["labor_rate_name"] == "Standard woodworking"
    assert result["price_id"] == future["id"]
    assert result["rate_per_hour"] == "123.456789"
    assert result["price_effective_date"] == "2099-01-01"
    assert Decimal(result["labor_hours"]) == Decimal("2.50")
    assert Decimal(result["total_cost"]) == Decimal("308.64197250")
    assert [item["rule_code"] for item in result["rules"]] == [
        "chair_base_assembly",
        "chair_leg_work",
        "chair_backrest_work",
    ]
    assert "currency" not in result


def test_costing_does_not_require_complete_3d_geometry(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    assert db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{seat['id']}",
        json={"depth": None, "thickness": None},
    ).status_code == 200
    finalized = finalize(db_client, draft)
    labor_rate = create_rate(db_client)
    add_price(
        db_client,
        labor_rate["id"],
        value="10",
        effective_date="2026-01-01",
    )

    response = db_client.get(cost_url(finalized["id"], labor_rate["id"]))

    assert response.status_code == 200
    assert Decimal(response.json()["total_cost"]) == Decimal("25")


def test_rejects_missing_price_inactive_rate_and_draft_plan(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    finalized = finalize(db_client, draft)

    no_price = create_rate(db_client)
    missing = db_client.get(cost_url(finalized["id"], no_price["id"]))
    assert missing.status_code == 409
    assert missing.json() == {
        "detail": "Selected labor rate has no price history"
    }

    inactive = create_rate(
        db_client,
        name="Inactive woodworking",
        is_active=False,
    )
    add_price(
        db_client,
        inactive["id"],
        value="10",
        effective_date="2026-01-01",
    )
    inactive_response = db_client.get(cost_url(finalized["id"], inactive["id"]))
    assert inactive_response.status_code == 409
    assert inactive_response.json() == {
        "detail": "Labor cost calculation requires an active labor rate"
    }

    active = create_rate(db_client, name="Draft rate")
    add_price(
        db_client,
        active["id"],
        value="10",
        effective_date="2026-01-01",
    )
    new_draft = create_draft(db_client)
    draft_response = db_client.get(cost_url(new_draft["id"], active["id"]))
    assert draft_response.status_code == 409
    assert draft_response.json() == {
        "detail": "Labor quantity estimation requires a finalized 2D plan"
    }


def test_costing_is_repeatable_read_only_and_reports_missing_resources(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    labor_rate = create_rate(db_client)
    add_price(
        db_client,
        labor_rate["id"],
        value="10",
        effective_date="2026-01-01",
    )
    plan_url = f"/api/v1/plans/{finalized['id']}"
    endpoint = cost_url(finalized["id"], labor_rate["id"])
    before = db_client.get(plan_url).json()

    first = db_client.get(endpoint)
    second = db_client.get(endpoint)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before
    assert db_client.get(
        cost_url(str(uuid4()), labor_rate["id"])
    ).status_code == 404
    assert db_client.get(
        cost_url(finalized["id"], str(uuid4()))
    ).status_code == 404
