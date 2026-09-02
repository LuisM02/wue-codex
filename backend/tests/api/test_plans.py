"""Real PostgreSQL API tests for editable parametric plans."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import PlanStatus
from app.models.furniture_plan import FurniturePlan

pytestmark = pytest.mark.integration

EXPECTED_NAMES = {
    "chair": [
        "seat",
        "backrest",
        "front_left_leg",
        "front_right_leg",
        "rear_left_leg",
        "rear_right_leg",
    ],
    "dining_table": [
        "tabletop",
        "front_left_leg",
        "front_right_leg",
        "rear_left_leg",
        "rear_right_leg",
    ],
    "bookshelf": [
        "left_side",
        "right_side",
        "top_panel",
        "bottom_panel",
        "back_panel",
        "shelf_1",
        "shelf_2",
        "shelf_3",
    ],
}


def create_furniture(
    client: TestClient,
    furniture_type: str = "chair",
    *,
    with_dimensions: bool = True,
) -> str:
    project = client.post("/api/v1/projects", json={"name": "2D plans"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Parametric item", "furniture_type": furniture_type},
    )
    furniture_id = furniture.json()["id"]
    if with_dimensions:
        response = client.put(
            f"/api/v1/furniture/{furniture_id}/dimensions",
            json={
                "width": "1000",
                "height": "1200",
                "depth": "600",
                "unit": "mm",
            },
        )
        assert response.status_code == 201
    return furniture_id


def generate_plan(client: TestClient, furniture_id: str) -> dict[str, object]:
    response = client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert response.status_code == 201
    return response.json()


@pytest.mark.parametrize("furniture_type", list(EXPECTED_NAMES))
def test_generates_defaults_reads_plan_and_locks_dimensions(
    db_client: TestClient,
    furniture_type: str,
) -> None:
    furniture_id = create_furniture(db_client, furniture_type)

    plan = generate_plan(db_client, furniture_id)

    assert plan["furniture_id"] == furniture_id
    assert plan["revision"] == 1
    assert plan["status"] == "draft"
    assert plan["furniture_type"] == furniture_type
    assert [item["component_name"] for item in plan["components"]] == (
        EXPECTED_NAMES[furniture_type]
    )
    assert all(item["quantity"] == 1 for item in plan["components"])

    dimensions_url = f"/api/v1/furniture/{furniture_id}/dimensions"
    dimensions = db_client.get(dimensions_url).json()
    assert dimensions["is_locked"] is True
    assert dimensions["locked_at"] is not None
    assert db_client.put(
        dimensions_url,
        json={"width": 1, "height": 1, "depth": 1, "unit": "m"},
    ).status_code == 409
    assert db_client.delete(dimensions_url).status_code == 409

    read = db_client.get(f"/api/v1/plans/{plan['id']}")
    listed = db_client.get(f"/api/v1/furniture/{furniture_id}/plans")
    assert read.status_code == 200
    assert read.json() == plan
    assert listed.status_code == 200
    assert listed.json() == [plan]


def test_generation_requires_dimensions_and_rejects_a_second_draft(
    db_client: TestClient,
) -> None:
    without_dimensions = create_furniture(db_client, with_dimensions=False)

    missing_dimensions = db_client.post(
        f"/api/v1/furniture/{without_dimensions}/plans"
    )

    assert missing_dimensions.status_code == 409
    assert missing_dimensions.json() == {
        "detail": "Overall dimensions are required before generating a 2D plan"
    }
    assert db_client.get(
        f"/api/v1/furniture/{without_dimensions}/plans"
    ).json() == []

    furniture_id = create_furniture(db_client)
    generate_plan(db_client, furniture_id)
    duplicate = db_client.post(f"/api/v1/furniture/{furniture_id}/plans")
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "detail": "Furniture already has an editable draft plan"
    }


def test_generation_requires_classified_furniture(db_client: TestClient) -> None:
    project = db_client.post("/api/v1/projects", json={"name": "AI workflow"})
    furniture = db_client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Unclassified piece"},
    )
    furniture_id = furniture.json()["id"]
    db_client.put(
        f"/api/v1/furniture/{furniture_id}/dimensions",
        json={"width": 800, "height": 900, "depth": 500, "unit": "mm"},
    )

    response = db_client.post(f"/api/v1/furniture/{furniture_id}/plans")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Furniture classification is required before generating a 2D plan"
    }


def test_unusable_dimensions_do_not_become_locked(db_client: TestClient) -> None:
    furniture_id = create_furniture(db_client, with_dimensions=False)
    dimensions_url = f"/api/v1/furniture/{furniture_id}/dimensions"
    assert db_client.put(
        dimensions_url,
        json={
            "width": "0.5",
            "height": "100",
            "depth": "100",
            "unit": "mm",
        },
    ).status_code == 201

    response = db_client.post(f"/api/v1/furniture/{furniture_id}/plans")

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Overall width, height, and depth must each be at least "
            "1.0000 millimeter for 2D generation"
        )
    }
    dimensions = db_client.get(dimensions_url).json()
    assert dimensions["is_locked"] is False
    assert dimensions["locked_at"] is None


def test_adds_updates_and_deletes_supported_draft_components(
    db_client: TestClient,
) -> None:
    furniture_id = create_furniture(db_client)
    plan = generate_plan(db_client, furniture_id)
    plan_url = f"/api/v1/plans/{plan['id']}"
    create_response = db_client.post(
        f"{plan_url}/components",
        json={
            "component_name": "arm_panel",
            "component_type": "panel",
            "width": "400",
            "height": "30",
            "thickness": "30",
            "x": "50",
            "y": "700",
            "z": "100",
            "quantity": 2,
            "sort_order": 20,
        },
    )

    assert create_response.status_code == 201
    component = create_response.json()
    assert component["component_name"] == "arm_panel"
    assert component["depth"] is None
    assert component["quantity"] == 2

    update_response = db_client.patch(
        f"{plan_url}/components/{component['id']}",
        json={
            "component_name": "arm_support",
            "component_type": "leg",
            "x": "-10.5",
            "rotation": "90",
            "depth": "25",
            "thickness": None,
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["component_name"] == "arm_support"
    assert updated["component_type"] == "leg"
    assert updated["x"] == "-10.5000"
    assert updated["rotation"] == "90.0000"
    assert updated["depth"] == "25.0000"
    assert updated["thickness"] is None

    delete_response = db_client.delete(
        f"{plan_url}/components/{component['id']}"
    )
    assert delete_response.status_code == 204
    names = [
        item["component_name"]
        for item in db_client.get(plan_url).json()["components"]
    ]
    assert "arm_support" not in names


def test_finalized_plan_component_mutations_are_rejected(
    db_client: TestClient,
    db_session: Session,
) -> None:
    furniture_id = create_furniture(db_client)
    plan = generate_plan(db_client, furniture_id)
    plan_model = db_session.get(FurniturePlan, UUID(str(plan["id"])))
    assert plan_model is not None
    plan_model.status = PlanStatus.FINALIZED
    db_session.commit()
    component_id = str(plan["components"][0]["id"])
    plan_url = f"/api/v1/plans/{plan['id']}"
    payload = {
        "component_name": "extra",
        "component_type": "panel",
        "width": 1,
        "height": 1,
    }

    add = db_client.post(f"{plan_url}/components", json=payload)
    update = db_client.patch(
        f"{plan_url}/components/{component_id}",
        json={"width": 2},
    )
    delete = db_client.delete(f"{plan_url}/components/{component_id}")

    expected = {"detail": "Finalized plans are immutable"}
    assert add.status_code == update.status_code == delete.status_code == 409
    assert add.json() == update.json() == delete.json() == expected


def test_plan_endpoints_report_missing_resources(db_client: TestClient) -> None:
    missing_id = uuid4()
    assert db_client.post(f"/api/v1/furniture/{missing_id}/plans").status_code == 404
    assert db_client.get(f"/api/v1/furniture/{missing_id}/plans").status_code == 404
    assert db_client.get(f"/api/v1/plans/{missing_id}").status_code == 404

    furniture_id = create_furniture(db_client)
    plan = generate_plan(db_client, furniture_id)
    assert db_client.patch(
        f"/api/v1/plans/{plan['id']}/components/{missing_id}",
        json={"width": 10},
    ).status_code == 404
