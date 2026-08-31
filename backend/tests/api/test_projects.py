"""Real PostgreSQL API tests for project CRUD."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_project_crud_lifecycle(db_client: TestClient) -> None:
    create_response = db_client.post(
        "/api/v1/projects",
        json={"name": "  Dining room  ", "description": "  Oak concept  "},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Dining room"
    assert created["description"] == "Oak concept"
    assert created["created_at"]
    assert created["updated_at"]

    project_id = created["id"]
    read_response = db_client.get(f"/api/v1/projects/{project_id}")
    assert read_response.status_code == 200
    assert read_response.json() == created

    update_response = db_client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Dining room revision", "description": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Dining room revision"
    assert update_response.json()["description"] is None

    list_response = db_client.get("/api/v1/projects")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [project_id]

    delete_response = db_client.delete(f"/api/v1/projects/{project_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert db_client.get(f"/api/v1/projects/{project_id}").status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_missing_project_returns_not_found(
    db_client: TestClient,
    method: str,
) -> None:
    project_id = uuid4()
    request = getattr(db_client, method)
    kwargs = {"json": {"name": "Updated"}} if method == "patch" else {}

    response = request(f"/api/v1/projects/{project_id}", **kwargs)

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


def test_project_api_validates_payload_and_pagination(db_client: TestClient) -> None:
    assert db_client.post("/api/v1/projects", json={"name": " "}).status_code == 422
    assert db_client.patch(f"/api/v1/projects/{uuid4()}", json={}).status_code == 422
    assert db_client.get("/api/v1/projects?offset=-1").status_code == 422
    assert db_client.get("/api/v1/projects?limit=101").status_code == 422
