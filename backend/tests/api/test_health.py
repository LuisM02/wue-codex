"""API tests for health endpoints."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db_session
from app.main import app


class SuccessfulResult:
    def scalar_one(self) -> int:
        return 1


class SuccessfulSession:
    def execute(self, statement: Any) -> SuccessfulResult:
        return SuccessfulResult()


class UnavailableSession:
    def execute(self, statement: Any) -> None:
        raise SQLAlchemyError("simulated connection failure")


def test_service_health_does_not_require_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "WUE API",
        "version": "0.5.0",
    }


def test_database_health_reports_reachable(client: TestClient) -> None:
    app.dependency_overrides[get_db_session] = lambda: SuccessfulSession()

    response = client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_database_health_reports_unavailable(client: TestClient) -> None:
    app.dependency_overrides[get_db_session] = lambda: UnavailableSession()

    response = client.get("/api/v1/health/database")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}


def test_missing_route_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404
