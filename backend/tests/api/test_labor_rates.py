"""Real PostgreSQL API tests for admin-managed labor rates."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


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


def test_rate_crud_listing_filter_and_duplicate_name(db_client: TestClient) -> None:
    standard = create_rate(db_client)
    specialist = create_rate(
        db_client,
        name="Specialist woodworking",
        is_active=False,
    )

    assert db_client.get(
        f"/api/v1/admin/labor-rates/{standard['id']}"
    ).json() == standard
    assert [
        item["rate_name"]
        for item in db_client.get("/api/v1/admin/labor-rates").json()
    ] == ["Specialist woodworking", "Standard woodworking"]
    assert db_client.get(
        "/api/v1/admin/labor-rates",
        params={"is_active": False},
    ).json() == [specialist]

    updated = db_client.patch(
        f"/api/v1/admin/labor-rates/{standard['id']}",
        json={"rate_name": "General woodworking", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["rate_name"] == "General woodworking"
    assert updated.json()["is_active"] is False

    duplicate = db_client.post(
        "/api/v1/admin/labor-rates",
        json={"rate_name": "Specialist woodworking"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "A labor rate with this name already exists"
    }

    assert db_client.delete(
        f"/api/v1/admin/labor-rates/{standard['id']}"
    ).status_code == 204
    assert db_client.get(
        f"/api/v1/admin/labor-rates/{standard['id']}"
    ).status_code == 404


def test_price_history_crud_orders_future_dates_without_today_filter(
    db_client: TestClient,
) -> None:
    labor_rate = create_rate(db_client)
    prices_url = f"/api/v1/admin/labor-rates/{labor_rate['id']}/prices"
    old = db_client.post(
        prices_url,
        json={"rate_per_hour": "100", "effective_date": "2025-01-01"},
    ).json()
    future_first = db_client.post(
        prices_url,
        json={"rate_per_hour": "200", "effective_date": "2099-01-01"},
    ).json()
    future_latest = db_client.post(
        prices_url,
        json={"rate_per_hour": "300.123456", "effective_date": "2099-01-01"},
    ).json()

    listed = db_client.get(prices_url)

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [
        future_latest["id"],
        future_first["id"],
        old["id"],
    ]
    assert db_client.get(
        f"/api/v1/admin/labor-rate-prices/{future_latest['id']}"
    ).json() == future_latest

    update = db_client.patch(
        f"/api/v1/admin/labor-rate-prices/{old['id']}",
        json={"rate_per_hour": "110.5", "effective_date": "2024-06-01"},
    )
    assert update.status_code == 200
    assert update.json()["rate_per_hour"] == "110.500000"

    assert db_client.delete(
        f"/api/v1/admin/labor-rate-prices/{future_first['id']}"
    ).status_code == 204


def test_rate_endpoints_report_missing_resources(db_client: TestClient) -> None:
    missing_id = uuid4()
    assert db_client.get(
        f"/api/v1/admin/labor-rates/{missing_id}"
    ).status_code == 404
    assert db_client.patch(
        f"/api/v1/admin/labor-rates/{missing_id}",
        json={"is_active": False},
    ).status_code == 404
    assert db_client.delete(
        f"/api/v1/admin/labor-rates/{missing_id}"
    ).status_code == 404
    assert db_client.post(
        f"/api/v1/admin/labor-rates/{missing_id}/prices",
        json={"rate_per_hour": 1, "effective_date": "2026-01-01"},
    ).status_code == 404
    assert db_client.get(
        f"/api/v1/admin/labor-rates/{missing_id}/prices"
    ).status_code == 404
    assert db_client.get(
        f"/api/v1/admin/labor-rate-prices/{missing_id}"
    ).status_code == 404
