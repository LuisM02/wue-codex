"""Real PostgreSQL API tests for the admin material catalog."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def create_material(
    client: TestClient,
    *,
    name: str = "Oak",
    material_type: str = "wood",
    unit: str = "board_ft",
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


def test_material_crud_listing_and_filters(db_client: TestClient) -> None:
    oak = create_material(db_client, name="Oak")
    screw = create_material(
        db_client,
        name="Wood screw",
        material_type="hardware",
        unit="piece",
        is_active=False,
    )

    assert oak["material_type"] == "wood"
    assert oak["unit"] == "board_ft"
    assert oak["is_active"] is True
    assert db_client.get(f"/api/v1/admin/materials/{oak['id']}").json() == oak

    all_materials = db_client.get("/api/v1/admin/materials").json()
    assert [item["material_name"] for item in all_materials] == [
        "Oak",
        "Wood screw",
    ]
    active_wood = db_client.get(
        "/api/v1/admin/materials",
        params={"material_type": "wood", "is_active": True},
    ).json()
    assert [item["id"] for item in active_wood] == [oak["id"]]
    inactive = db_client.get(
        "/api/v1/admin/materials",
        params={"is_active": False},
    ).json()
    assert [item["id"] for item in inactive] == [screw["id"]]

    updated = db_client.patch(
        f"/api/v1/admin/materials/{oak['id']}",
        json={"material_name": "White oak", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["material_name"] == "White oak"
    assert updated.json()["is_active"] is False

    deleted = db_client.delete(f"/api/v1/admin/materials/{oak['id']}")
    assert deleted.status_code == 204
    assert db_client.get(f"/api/v1/admin/materials/{oak['id']}").status_code == 404


def test_rejects_duplicate_names_and_invalid_pairs(db_client: TestClient) -> None:
    create_material(db_client, name="Mahogany")

    duplicate = db_client.post(
        "/api/v1/admin/materials",
        json={
            "material_name": "Mahogany",
            "material_type": "wood",
            "unit": "m3",
        },
    )
    invalid = db_client.post(
        "/api/v1/admin/materials",
        json={
            "material_name": "Impossible wood",
            "material_type": "wood",
            "unit": "piece",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "A material with this name already exists"
    }
    assert invalid.status_code == 422


def test_unit_can_change_before_but_not_after_price_history(
    db_client: TestClient,
) -> None:
    material = create_material(db_client, unit="mm3")
    changed = db_client.patch(
        f"/api/v1/admin/materials/{material['id']}",
        json={"unit": "cm3"},
    )
    assert changed.status_code == 200
    assert changed.json()["unit"] == "cm3"
    price = db_client.post(
        f"/api/v1/admin/materials/{material['id']}/prices",
        json={"price_per_unit": "1.25", "effective_date": "2026-01-01"},
    )
    assert price.status_code == 201
    assert price.json()["unit"] == "cm3"

    blocked = db_client.patch(
        f"/api/v1/admin/materials/{material['id']}",
        json={"unit": "m3"},
    )
    incompatible = db_client.patch(
        f"/api/v1/admin/materials/{material['id']}",
        json={"material_type": "hardware"},
    )

    assert blocked.status_code == 409
    assert blocked.json() == {
        "detail": "Material type and unit cannot change after price history exists"
    }
    assert incompatible.status_code == 409
    assert incompatible.json() == {
        "detail": "Material type and unit are incompatible"
    }


def test_price_history_crud_orders_future_dates_without_today_filter(
    db_client: TestClient,
) -> None:
    material = create_material(db_client, name="Pine", unit="m3")
    price_url = f"/api/v1/admin/materials/{material['id']}/prices"
    old = db_client.post(
        price_url,
        json={"price_per_unit": "10", "effective_date": "2025-01-01"},
    ).json()
    future_first = db_client.post(
        price_url,
        json={"price_per_unit": "20", "effective_date": "2099-01-01"},
    ).json()
    future_latest = db_client.post(
        price_url,
        json={"price_per_unit": "30.123456", "effective_date": "2099-01-01"},
    ).json()

    listed = db_client.get(price_url)

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [
        future_latest["id"],
        future_first["id"],
        old["id"],
    ]
    assert all(item["unit"] == "m3" for item in listed.json())
    assert db_client.get(
        f"/api/v1/admin/material-prices/{future_latest['id']}"
    ).json() == future_latest

    update = db_client.patch(
        f"/api/v1/admin/material-prices/{old['id']}",
        json={"price_per_unit": "11.5", "effective_date": "2024-06-01"},
    )
    assert update.status_code == 200
    assert update.json()["price_per_unit"] == "11.500000"
    assert update.json()["unit"] == "m3"

    deleted = db_client.delete(
        f"/api/v1/admin/material-prices/{future_first['id']}"
    )
    assert deleted.status_code == 204
    assert db_client.get(
        f"/api/v1/admin/material-prices/{future_first['id']}"
    ).status_code == 404


def test_material_endpoints_report_missing_resources(db_client: TestClient) -> None:
    missing_id = uuid4()
    assert db_client.get(f"/api/v1/admin/materials/{missing_id}").status_code == 404
    assert db_client.patch(
        f"/api/v1/admin/materials/{missing_id}",
        json={"is_active": False},
    ).status_code == 404
    assert db_client.delete(
        f"/api/v1/admin/materials/{missing_id}"
    ).status_code == 404
    assert db_client.post(
        f"/api/v1/admin/materials/{missing_id}/prices",
        json={"price_per_unit": 1, "effective_date": "2026-01-01"},
    ).status_code == 404
    assert db_client.get(
        f"/api/v1/admin/materials/{missing_id}/prices"
    ).status_code == 404
    assert db_client.get(
        f"/api/v1/admin/material-prices/{missing_id}"
    ).status_code == 404
