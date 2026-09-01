"""Real PostgreSQL API tests for read-only hardware cost calculation."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def create_draft(client: TestClient) -> dict:
    project = client.post("/api/v1/projects", json={"name": "Hardware cost"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Cost source", "furniture_type": "chair"},
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


def create_material(
    client: TestClient,
    *,
    name: str,
    material_type: str = "hardware",
    unit: str = "piece",
    is_active: bool = True,
) -> dict:
    response = client.post(
        "/api/v1/admin/materials",
        json={
            "material_name": name,
            "material_type": material_type,
            "unit": unit,
            "is_active": is_active,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_price(
    client: TestClient,
    material_id: str,
    *,
    value: str,
    effective_date: str,
) -> dict:
    response = client.post(
        f"/api/v1/admin/materials/{material_id}/prices",
        json={"price_per_unit": value, "effective_date": effective_date},
    )
    assert response.status_code == 201
    return response.json()


def cost_url(plan_id: str, material_id: str) -> str:
    return f"/api/v1/plans/{plan_id}/hardware-cost?material_id={material_id}"


def test_uses_future_latest_piece_price_and_returns_live_breakdown(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    hardware = create_material(db_client, name="WOOD SCREW")
    add_price(
        db_client,
        hardware["id"],
        value="1.25",
        effective_date="2020-01-01",
    )
    future = add_price(
        db_client,
        hardware["id"],
        value="2.5",
        effective_date="2099-01-01",
    )

    response = db_client.get(cost_url(finalized["id"], hardware["id"]))

    assert response.status_code == 200
    result = response.json()
    assert result["plan_id"] == finalized["id"]
    assert result["material_id"] == hardware["id"]
    assert result["material_name"] == "WOOD SCREW"
    assert result["price_id"] == future["id"]
    assert result["price_per_piece"] == "2.500000"
    assert result["price_unit"] == "piece"
    assert result["price_effective_date"] == "2099-01-01"
    assert result["quantity"] == 10
    assert Decimal(result["total_cost"]) == Decimal("25")
    assert [item["screw_quantity"] for item in result["connections"]] == [8, 2]
    assert "currency" not in result


def test_preserves_exact_decimal_cost_and_does_not_require_3d(
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
    hardware = create_material(db_client, name="Wood screw")
    add_price(
        db_client,
        hardware["id"],
        value="0.333333",
        effective_date="2026-01-01",
    )

    result = db_client.get(cost_url(finalized["id"], hardware["id"])).json()

    assert result["quantity"] == 10
    assert Decimal(result["total_cost"]) == Decimal("3.333330")


def test_rejects_missing_price_and_invalid_hardware_selection(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))

    no_price = create_material(db_client, name="Wood screw")
    missing = db_client.get(cost_url(finalized["id"], no_price["id"]))
    assert missing.status_code == 409
    assert missing.json() == {"detail": "Selected hardware has no price history"}

    inactive = create_material(
        db_client,
        name="WOOD SCREW",
        is_active=False,
    )
    add_price(
        db_client,
        inactive["id"],
        value="1",
        effective_date="2026-01-01",
    )
    inactive_response = db_client.get(cost_url(finalized["id"], inactive["id"]))
    assert inactive_response.status_code == 409
    assert inactive_response.json() == {
        "detail": "Hardware cost calculation requires an active material"
    }

    wood = create_material(
        db_client,
        name="Wood screw timber",
        material_type="wood",
        unit="mm3",
    )
    add_price(
        db_client,
        wood["id"],
        value="1",
        effective_date="2026-01-01",
    )
    wood_response = db_client.get(cost_url(finalized["id"], wood["id"]))
    assert wood_response.status_code == 409
    assert wood_response.json() == {
        "detail": "Hardware cost calculation requires a hardware material"
    }

    wrong_name = create_material(db_client, name="Machine screw")
    add_price(
        db_client,
        wrong_name["id"],
        value="1",
        effective_date="2026-01-01",
    )
    name_response = db_client.get(cost_url(finalized["id"], wrong_name["id"]))
    assert name_response.status_code == 409
    assert name_response.json() == {
        "detail": "Hardware cost calculation requires material name Wood screw"
    }


def test_requires_finalized_plan_and_reports_missing_resources(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    hardware = create_material(db_client, name="Wood screw")
    add_price(
        db_client,
        hardware["id"],
        value="1",
        effective_date="2026-01-01",
    )

    draft_response = db_client.get(cost_url(draft["id"], hardware["id"]))
    assert draft_response.status_code == 409
    assert draft_response.json() == {
        "detail": "Hardware quantity estimation requires a finalized 2D plan"
    }
    assert db_client.get(cost_url(str(uuid4()), hardware["id"])).status_code == 404
    assert db_client.get(cost_url(draft["id"], str(uuid4()))).status_code == 404


def test_costing_is_repeatable_and_read_only(db_client: TestClient) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    hardware = create_material(db_client, name="Wood screw")
    add_price(
        db_client,
        hardware["id"],
        value="1",
        effective_date="2026-01-01",
    )
    plan_url = f"/api/v1/plans/{finalized['id']}"
    cost_endpoint = cost_url(finalized["id"], hardware["id"])
    before = db_client.get(plan_url).json()

    first = db_client.get(cost_endpoint)
    second = db_client.get(cost_endpoint)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before
