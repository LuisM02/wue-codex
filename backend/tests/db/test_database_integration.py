"""Real PostgreSQL integration coverage for foundation behavior."""

from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.db.base import Base

pytestmark = pytest.mark.integration
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_database_health_against_postgresql(db_client: TestClient) -> None:
    response = db_client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_database_is_at_migration_head(postgres_engine: Engine) -> None:
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    expected_head = ScriptDirectory.from_config(alembic_config).get_current_head()

    with postgres_engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()

    assert current_revision == expected_head


def test_migration_matches_orm_metadata(postgres_engine: Engine) -> None:
    with postgres_engine.connect() as connection:
        migration_context = MigrationContext.configure(
            connection,
            opts={"compare_type": True},
        )
        differences = compare_metadata(migration_context, Base.metadata)

    assert differences == []
