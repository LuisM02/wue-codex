"""Real PostgreSQL API tests for complete costs and quotation snapshots."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.furniture_plan import FurniturePlan
from app.models.quotation import Quotation

pytestmark = pytest.mark.integration


def create_plan(client: TestClient, *, finalize: bool = True) -> dict:
    project = client.post("/api/v1/projects", json={"name": "Quotation"}).json()
    furniture = client.post(
        f"/api/v1/projects/{project['id']}/furniture",
        json={"name": "Quoted chair", "furniture_type": "chair"},
    ).json()
    assert client.put(
        f"/api/v1/furniture/{furniture['id']}/dimensions",
        json={"width": 1000, "height": 1200, "depth": 600, "unit": "mm"},
    ).status_code == 201
    draft = client.post(f"/api/v1/furniture/{furniture['id']}/plans").json()
    if not finalize:
        return draft
    response = client.post(f"/api/v1/plans/{draft['id']}/finalize")
    assert response.status_code == 200
    return response.json()


def create_material(
    client: TestClient,
    *,
    name: str,
    material_type: str,
    unit: str,
) -> dict:
    response = client.post(
        "/api/v1/admin/materials",
        json={
            "material_name": name,
            "material_type": material_type,
            "unit": unit,
        },
    )
    assert response.status_code == 201
    return response.json()


def add_material_price(
    client: TestClient,
    material_id: str,
    value: str,
    effective_date: str = "2026-01-01",
) -> dict:
    response = client.post(
        f"/api/v1/admin/materials/{material_id}/prices",
        json={"price_per_unit": value, "effective_date": effective_date},
    )
    assert response.status_code == 201
    return response.json()


def create_labor_rate(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/admin/labor-rates",
        json={"rate_name": "Standard woodworking"},
    )
    assert response.status_code == 201
    return response.json()


def add_labor_price(
    client: TestClient,
    labor_rate_id: str,
    value: str,
    effective_date: str = "2026-01-01",
) -> dict:
    response = client.post(
        f"/api/v1/admin/labor-rates/{labor_rate_id}/prices",
        json={"rate_per_hour": value, "effective_date": effective_date},
    )
    assert response.status_code == 201
    return response.json()


def create_selection(client: TestClient) -> dict[str, dict]:
    wood = create_material(
        client,
        name="Quoted oak",
        material_type="wood",
        unit="mm3",
    )
    hardware = create_material(
        client,
        name="Wood screw",
        material_type="hardware",
        unit="piece",
    )
    labor_rate = create_labor_rate(client)
    add_material_price(client, wood["id"], "0.000001")
    add_material_price(client, hardware["id"], "2")
    add_labor_price(client, labor_rate["id"], "100")
    return {"wood": wood, "hardware": hardware, "labor_rate": labor_rate}


def selection_payload(selection: dict[str, dict]) -> dict[str, str]:
    return {
        "material_id": selection["wood"]["id"],
        "hardware_material_id": selection["hardware"]["id"],
        "labor_rate_id": selection["labor_rate"]["id"],
    }


def complete_cost_url(plan_id: str, selection: dict[str, dict]) -> str:
    payload = selection_payload(selection)
    return (
        f"/api/v1/plans/{plan_id}/complete-cost"
        f"?material_id={payload['material_id']}"
        f"&hardware_material_id={payload['hardware_material_id']}"
        f"&labor_rate_id={payload['labor_rate_id']}"
    )


def test_complete_cost_combines_exactly_three_domains_without_overhead(
    db_client: TestClient,
) -> None:
    finalized = create_plan(db_client)
    selection = create_selection(db_client)

    response = db_client.get(complete_cost_url(finalized["id"], selection))

    assert response.status_code == 200
    result = response.json()
    material_cost = Decimal(result["material"]["total_cost"])
    hardware_cost = Decimal(result["hardware"]["total_cost"])
    labor_cost = Decimal(result["labor"]["total_cost"])
    assert material_cost == Decimal("38.4768")
    assert hardware_cost == Decimal("20")
    assert labor_cost == Decimal("250")
    assert Decimal(result["total_cost"]) == Decimal("308.4768")
    assert Decimal(result["total_cost"]) == material_cost + hardware_cost + labor_cost
    assert "overhead" not in result
    assert "currency" not in result


def test_quotation_snapshots_costs_and_does_not_accept_client_totals(
    db_client: TestClient,
) -> None:
    finalized = create_plan(db_client)
    selection = create_selection(db_client)
    endpoint = f"/api/v1/plans/{finalized['id']}/quotations"
    payload = selection_payload(selection)

    rejected = db_client.post(endpoint, json={**payload, "total_cost": "1"})
    assert rejected.status_code == 422

    created = db_client.post(endpoint, json=payload)

    assert created.status_code == 201
    quotation = created.json()
    assert quotation["quotation_number"].startswith("WUE-")
    assert quotation["plan_revision"] == finalized["revision"]
    assert Decimal(quotation["wood_material_cost"]) == Decimal("38.4768")
    assert quotation["hardware_quantity"] == 10
    assert Decimal(quotation["labor_hours"]) == Decimal("2.50")
    assert Decimal(quotation["total_cost"]) == Decimal("308.4768")
    assert "overhead" not in quotation
    assert "currency" not in quotation
    assert db_client.get(
        f"/api/v1/quotations/{quotation['id']}"
    ).json() == quotation


def test_old_quotation_remains_stable_after_prices_change(
    db_client: TestClient,
) -> None:
    finalized = create_plan(db_client)
    selection = create_selection(db_client)
    endpoint = f"/api/v1/plans/{finalized['id']}/quotations"
    payload = selection_payload(selection)
    first = db_client.post(endpoint, json=payload).json()

    add_material_price(
        db_client,
        selection["wood"]["id"],
        "0.000002",
        "2099-01-01",
    )
    add_material_price(
        db_client,
        selection["hardware"]["id"],
        "3",
        "2099-01-01",
    )
    add_labor_price(
        db_client,
        selection["labor_rate"]["id"],
        "200",
        "2099-01-01",
    )
    second = db_client.post(endpoint, json=payload).json()

    assert Decimal(first["total_cost"]) == Decimal("308.4768")
    assert Decimal(second["total_cost"]) == Decimal("606.9536")
    assert db_client.get(f"/api/v1/quotations/{first['id']}").json() == first
    listed = db_client.get(endpoint).json()
    assert [item["id"] for item in listed] == [second["id"], first["id"]]


def test_workflow_and_selected_resource_errors_are_clear(
    db_client: TestClient,
) -> None:
    draft = create_plan(db_client, finalize=False)
    selection = create_selection(db_client)
    draft_response = db_client.get(complete_cost_url(draft["id"], selection))
    assert draft_response.status_code == 409

    finalized = create_plan(db_client)
    payload = selection_payload(selection)
    missing_wood = db_client.get(
        complete_cost_url(
            finalized["id"],
            {**selection, "wood": {"id": str(uuid4())}},
        )
    )
    assert missing_wood.status_code == 404
    assert missing_wood.json() == {"detail": "Wood material not found"}
    assert db_client.post(
        f"/api/v1/plans/{uuid4()}/quotations",
        json=payload,
    ).status_code == 404


def test_database_enforces_total_and_plan_delete_cascades_quotation(
    db_client: TestClient,
    db_session: Session,
) -> None:
    finalized = create_plan(db_client)
    selection = create_selection(db_client)
    quotation = db_client.post(
        f"/api/v1/plans/{finalized['id']}/quotations",
        json=selection_payload(selection),
    ).json()
    quotation_id = UUID(quotation["id"])

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    "UPDATE quotations SET total_cost = total_cost + 1 "
                    "WHERE id = :quotation_id"
                ),
                {"quotation_id": quotation_id},
            )

    plan = db_session.get(FurniturePlan, UUID(finalized["id"]))
    assert plan is not None
    db_session.delete(plan)
    db_session.commit()
    assert db_session.get(Quotation, quotation_id) is None


def test_quotation_delete_and_missing_resources(db_client: TestClient) -> None:
    finalized = create_plan(db_client)
    selection = create_selection(db_client)
    quotation = db_client.post(
        f"/api/v1/plans/{finalized['id']}/quotations",
        json=selection_payload(selection),
    ).json()

    assert db_client.delete(
        f"/api/v1/quotations/{quotation['id']}"
    ).status_code == 204
    assert db_client.get(
        f"/api/v1/quotations/{quotation['id']}"
    ).status_code == 404
    assert db_client.get(
        f"/api/v1/plans/{uuid4()}/quotations"
    ).status_code == 404
