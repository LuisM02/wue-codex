"""Real PostgreSQL API tests for read-only material cost calculation."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.support.photo_reconstruction import prepare_test_reconstruction

pytestmark = pytest.mark.integration


def create_draft(client: TestClient) -> dict:
    project = client.post("/api/v1/projects", json={"name": "Material cost"})
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
    prepare_test_reconstruction(client, furniture_id)
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
    name: str = "Costed oak",
    material_type: str = "wood",
    unit: str = "cm3",
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
    return f"/api/v1/plans/{plan_id}/material-cost?material_id={material_id}"


def test_uses_future_latest_price_and_returns_component_breakdown(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    material = create_material(db_client)
    add_price(
        db_client,
        material["id"],
        value="2",
        effective_date="2020-01-01",
    )
    future = add_price(
        db_client,
        material["id"],
        value="3",
        effective_date="2099-01-01",
    )

    response = db_client.get(cost_url(finalized["id"], material["id"]))

    assert response.status_code == 200
    result = response.json()
    assert result["plan_id"] == finalized["id"]
    assert result["material_id"] == material["id"]
    assert result["material_name"] == "Costed oak"
    assert result["price_id"] == future["id"]
    assert result["price_per_unit"] == "3.000000"
    assert result["price_unit"] == "cm3"
    assert result["price_effective_date"] == "2099-01-01"
    assert Decimal(result["total_volume_mm3"]) == Decimal("38476800")
    assert Decimal(result["total_quantity_in_price_unit"]) == Decimal("38476.8")
    assert Decimal(result["total_cost"]) == Decimal("115430.4")
    assert sum(
        (Decimal(item["cost"]) for item in result["components"]),
        start=Decimal("0"),
    ) == Decimal(result["total_cost"])


def test_mm3_pricing_preserves_exact_decimal_cost(db_client: TestClient) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    material = create_material(db_client, name="Fine price", unit="mm3")
    price = add_price(
        db_client,
        material["id"],
        value="0.000001",
        effective_date="2026-01-01",
    )

    result = db_client.get(cost_url(finalized["id"], material["id"])).json()

    assert result["price_id"] == price["id"]
    assert Decimal(result["total_cost"]) == Decimal("38.4768")


def test_rejects_missing_price_inactive_material_and_hardware(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    no_price = create_material(db_client, name="No price")
    missing = db_client.get(cost_url(finalized["id"], no_price["id"]))
    assert missing.status_code == 409
    assert missing.json() == {"detail": "Selected material has no price history"}

    inactive = create_material(db_client, name="Inactive", is_active=False)
    add_price(
        db_client,
        inactive["id"],
        value="1",
        effective_date="2026-01-01",
    )
    inactive_response = db_client.get(cost_url(finalized["id"], inactive["id"]))
    assert inactive_response.status_code == 409
    assert inactive_response.json() == {
        "detail": "Material cost calculation requires an active material"
    }

    hardware = create_material(
        db_client,
        name="Wood screw",
        material_type="hardware",
        unit="piece",
    )
    add_price(
        db_client,
        hardware["id"],
        value="1",
        effective_date="2026-01-01",
    )
    hardware_response = db_client.get(cost_url(finalized["id"], hardware["id"]))
    assert hardware_response.status_code == 409
    assert hardware_response.json() == {
        "detail": "Material cost calculation requires a wood material"
    }


def test_costing_requires_finalized_complete_geometry(db_client: TestClient) -> None:
    draft = create_draft(db_client)
    material = create_material(db_client)
    add_price(
        db_client,
        material["id"],
        value="1",
        effective_date="2026-01-01",
    )
    assert db_client.get(cost_url(draft["id"], material["id"])).status_code == 409

    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    assert db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{seat['id']}",
        json={"depth": None, "thickness": None},
    ).status_code == 200
    finalized = finalize(db_client, draft)

    incomplete = db_client.get(cost_url(finalized["id"], material["id"]))
    assert incomplete.status_code == 409
    assert "neither depth nor thickness: seat" in incomplete.json()["detail"]


def test_costing_is_repeatable_read_only_and_reports_missing_resources(
    db_client: TestClient,
) -> None:
    finalized = finalize(db_client, create_draft(db_client))
    material = create_material(db_client)
    add_price(
        db_client,
        material["id"],
        value="1",
        effective_date="2026-01-01",
    )
    plan_url = f"/api/v1/plans/{finalized['id']}"
    before = db_client.get(plan_url).json()

    first = db_client.get(cost_url(finalized["id"], material["id"]))
    second = db_client.get(cost_url(finalized["id"], material["id"]))

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert db_client.get(plan_url).json() == before
    assert db_client.get(cost_url(str(uuid4()), material["id"])).status_code == 404
    assert db_client.get(cost_url(finalized["id"], str(uuid4()))).status_code == 404
