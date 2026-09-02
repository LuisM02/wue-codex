"""Real PostgreSQL API tests for furniture CRUD and ownership."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def create_project(client: TestClient, name: str = "Project") -> str:
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize("furniture_type", ["chair", "dining_table", "bookshelf"])
def test_create_each_supported_furniture_type(
    db_client: TestClient,
    furniture_type: str,
) -> None:
    project_id = create_project(db_client)

    response = db_client.post(
        f"/api/v1/projects/{project_id}/furniture",
        json={"name": "  Design 1  ", "furniture_type": furniture_type},
    )

    assert response.status_code == 201
    assert response.json()["project_id"] == project_id
    assert response.json()["name"] == "Design 1"
    assert response.json()["furniture_type"] == furniture_type


def test_create_furniture_without_preselecting_type(db_client: TestClient) -> None:
    project_id = create_project(db_client)

    response = db_client.post(
        f"/api/v1/projects/{project_id}/furniture",
        json={"name": "Piece awaiting image analysis"},
    )

    assert response.status_code == 201
    assert response.json()["furniture_type"] is None


@pytest.mark.parametrize("furniture_type", ["bed", "sofa", "lamp_shade"])
def test_rejects_out_of_scope_furniture_types(
    db_client: TestClient,
    furniture_type: str,
) -> None:
    project_id = create_project(db_client)

    response = db_client.post(
        f"/api/v1/projects/{project_id}/furniture",
        json={"name": "Unsupported", "furniture_type": furniture_type},
    )

    assert response.status_code == 422


def test_furniture_crud_and_project_scoped_listing(db_client: TestClient) -> None:
    first_project_id = create_project(db_client, "First")
    second_project_id = create_project(db_client, "Second")
    create_response = db_client.post(
        f"/api/v1/projects/{first_project_id}/furniture",
        json={"name": "Chair A", "furniture_type": "chair"},
    )
    furniture_id = create_response.json()["id"]
    db_client.post(
        f"/api/v1/projects/{second_project_id}/furniture",
        json={"name": "Shelf B", "furniture_type": "bookshelf"},
    )

    list_response = db_client.get(
        f"/api/v1/projects/{first_project_id}/furniture"
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [furniture_id]

    read_response = db_client.get(f"/api/v1/furniture/{furniture_id}")
    assert read_response.status_code == 200

    update_response = db_client.patch(
        f"/api/v1/furniture/{furniture_id}",
        json={"name": "Table A", "furniture_type": "dining_table"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Table A"
    assert update_response.json()["furniture_type"] == "dining_table"

    delete_response = db_client.delete(f"/api/v1/furniture/{furniture_id}")
    assert delete_response.status_code == 204
    assert db_client.get(f"/api/v1/furniture/{furniture_id}").status_code == 404


def test_missing_resources_return_plain_not_found_details(db_client: TestClient) -> None:
    missing_project_id = uuid4()
    missing_furniture_id = uuid4()

    create_response = db_client.post(
        f"/api/v1/projects/{missing_project_id}/furniture",
        json={"name": "Chair", "furniture_type": "chair"},
    )
    list_response = db_client.get(
        f"/api/v1/projects/{missing_project_id}/furniture"
    )
    furniture_response = db_client.get(
        f"/api/v1/furniture/{missing_furniture_id}"
    )

    assert create_response.status_code == 404
    assert create_response.json() == {"detail": "Project not found"}
    assert list_response.status_code == 404
    assert list_response.json() == {"detail": "Project not found"}
    assert furniture_response.status_code == 404
    assert furniture_response.json() == {"detail": "Furniture not found"}


def test_deleting_project_cascades_to_its_furniture(db_client: TestClient) -> None:
    project_id = create_project(db_client)
    create_response = db_client.post(
        f"/api/v1/projects/{project_id}/furniture",
        json={"name": "Chair", "furniture_type": "chair"},
    )
    furniture_id = create_response.json()["id"]

    assert db_client.delete(f"/api/v1/projects/{project_id}").status_code == 204
    response = db_client.get(f"/api/v1/furniture/{furniture_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Furniture not found"}
