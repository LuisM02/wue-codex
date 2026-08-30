"""Real PostgreSQL integration coverage for the database health endpoint."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.session import get_db_session
from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
def postgres_session() -> Generator[Session, None, None]:
    database_url = os.getenv("WUE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("WUE_TEST_DATABASE_URL is not configured")

    validated_url = Settings(_env_file=None, database_url=database_url).database_url
    integration_engine = create_engine(validated_url, pool_pre_ping=True)
    integration_session_factory = sessionmaker(bind=integration_engine, class_=Session)

    try:
        with integration_session_factory() as session:
            yield session
    finally:
        integration_engine.dispose()


def test_database_health_against_postgresql(postgres_session: Session) -> None:
    app.dependency_overrides[get_db_session] = lambda: postgres_session

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/database")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}
