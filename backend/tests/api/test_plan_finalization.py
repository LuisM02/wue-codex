"""Real PostgreSQL API tests for finalization and design revisions."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

GEOMETRY_FIELDS = (
    "component_name",
    "component_type",
    "width",
    "height",
    "depth",
    "thickness",
    "x",
    "y",
    "z",
    "rotation",
    "quantity",
    "sort_order",
)


def create_draft(client: TestClient, furniture_type: str = "chair") -> dict:
    project = client.post("/api/v1/projects", json={"name": "Finalization"})
    furniture = client.post(
        f"/api/v1/projects/{project.json()['id']}/furniture",
        json={"name": "Versioned item", "furniture_type": furniture_type},
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


def geometry(component: dict) -> dict:
    return {field: component[field] for field in GEOMETRY_FIELDS}


@pytest.mark.parametrize("furniture_type", ["chair", "dining_table", "bookshelf"])
def test_finalizes_each_valid_default_exactly_once(
    db_client: TestClient,
    furniture_type: str,
) -> None:
    draft = create_draft(db_client, furniture_type)
    before_geometry = [geometry(item) for item in draft["components"]]

    response = db_client.post(f"/api/v1/plans/{draft['id']}/finalize")

    assert response.status_code == 200
    finalized = response.json()
    assert finalized["id"] == draft["id"]
    assert finalized["status"] == "finalized"
    assert [geometry(item) for item in finalized["components"]] == before_geometry

    repeated = db_client.post(f"/api/v1/plans/{draft['id']}/finalize")
    assert repeated.status_code == 409
    assert repeated.json() == {"detail": "Finalized plans are immutable"}


def test_invalid_semantics_leave_draft_editable_until_repaired(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    seat = next(
        item for item in draft["components"] if item["component_name"] == "seat"
    )
    plan_url = f"/api/v1/plans/{draft['id']}"
    assert db_client.delete(
        f"{plan_url}/components/{seat['id']}"
    ).status_code == 204

    invalid = db_client.post(f"{plan_url}/finalize")

    assert invalid.status_code == 409
    assert invalid.json() == {
        "detail": "Plan cannot be finalized: chair requires exactly one seat panel (found 0)"
    }
    assert db_client.get(plan_url).json()["status"] == "draft"

    replacement = {field: seat[field] for field in GEOMETRY_FIELDS}
    assert db_client.post(
        f"{plan_url}/components",
        json=replacement,
    ).status_code == 201
    repaired = db_client.post(f"{plan_url}/finalize")
    assert repaired.status_code == 200
    assert repaired.json()["status"] == "finalized"


def test_unrecognized_component_blocks_finalization(db_client: TestClient) -> None:
    draft = create_draft(db_client, "dining_table")
    plan_url = f"/api/v1/plans/{draft['id']}"
    added = db_client.post(
        f"{plan_url}/components",
        json={
            "component_name": "apron",
            "component_type": "panel",
            "width": 500,
            "height": 50,
            "thickness": 20,
        },
    )
    assert added.status_code == 201

    response = db_client.post(f"{plan_url}/finalize")

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Plan cannot be finalized: unrecognized dining_table "
            "components: apron:panel"
        )
    }


def test_revision_deep_copies_finalized_geometry_into_next_draft(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client, "bookshelf")
    shelf = next(
        item for item in draft["components"] if item["component_name"] == "shelf_2"
    )
    patch = db_client.patch(
        f"/api/v1/plans/{draft['id']}/components/{shelf['id']}",
        json={"y": "575.5", "depth": None, "thickness": "22"},
    )
    assert patch.status_code == 200
    finalized_response = db_client.post(
        f"/api/v1/plans/{draft['id']}/finalize"
    )
    assert finalized_response.status_code == 200
    finalized = finalized_response.json()

    revision_response = db_client.post(
        f"/api/v1/plans/{finalized['id']}/revisions"
    )

    assert revision_response.status_code == 201
    revision = revision_response.json()
    assert revision["revision"] == 2
    assert revision["status"] == "draft"
    assert revision["furniture_type"] == "bookshelf"
    assert [geometry(item) for item in revision["components"]] == [
        geometry(item) for item in finalized["components"]
    ]
    assert {item["id"] for item in revision["components"]}.isdisjoint(
        {item["id"] for item in finalized["components"]}
    )
    assert all(item["plan_id"] == revision["id"] for item in revision["components"])

    revision_shelf = next(
        item
        for item in revision["components"]
        if item["component_name"] == "shelf_2"
    )
    changed = db_client.patch(
        f"/api/v1/plans/{revision['id']}/components/{revision_shelf['id']}",
        json={"y": "600"},
    )
    assert changed.status_code == 200
    source_shelf = next(
        item
        for item in db_client.get(f"/api/v1/plans/{finalized['id']}").json()[
            "components"
        ]
        if item["component_name"] == "shelf_2"
    )
    assert source_shelf["y"] == "575.5000"

    duplicate_draft = db_client.post(
        f"/api/v1/plans/{finalized['id']}/revisions"
    )
    assert duplicate_draft.status_code == 409
    assert duplicate_draft.json() == {
        "detail": "Furniture already has an editable draft plan"
    }


def test_finalized_revision_can_produce_revision_three(
    db_client: TestClient,
) -> None:
    first = create_draft(db_client)
    finalized_first = db_client.post(
        f"/api/v1/plans/{first['id']}/finalize"
    ).json()
    second = db_client.post(
        f"/api/v1/plans/{finalized_first['id']}/revisions"
    ).json()
    finalized_second = db_client.post(
        f"/api/v1/plans/{second['id']}/finalize"
    ).json()

    third = db_client.post(
        f"/api/v1/plans/{finalized_second['id']}/revisions"
    )

    assert third.status_code == 201
    assert third.json()["revision"] == 3
    plans = db_client.get(
        f"/api/v1/furniture/{first['furniture_id']}/plans"
    ).json()
    assert [(item["revision"], item["status"]) for item in plans] == [
        (1, "finalized"),
        (2, "finalized"),
        (3, "draft"),
    ]


def test_draft_cannot_be_used_as_revision_source(db_client: TestClient) -> None:
    draft = create_draft(db_client)

    response = db_client.post(f"/api/v1/plans/{draft['id']}/revisions")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Only a finalized plan can be used to create a revision"
    }


def test_initial_generation_cannot_bypass_revision_copy(
    db_client: TestClient,
) -> None:
    draft = create_draft(db_client)
    finalized = db_client.post(
        f"/api/v1/plans/{draft['id']}/finalize"
    ).json()

    response = db_client.post(
        f"/api/v1/furniture/{finalized['furniture_id']}/plans"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Furniture already has a plan; create a revision from a "
            "finalized plan"
        )
    }


def test_finalization_and_revision_report_missing_plan(db_client: TestClient) -> None:
    missing_id = uuid4()

    assert db_client.post(f"/api/v1/plans/{missing_id}/finalize").status_code == 404
    assert db_client.post(f"/api/v1/plans/{missing_id}/revisions").status_code == 404
