"""Shared pytest fixtures."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db_session
from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    database_url = os.getenv("WUE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("WUE_TEST_DATABASE_URL is not configured")
    return Settings(_env_file=None, database_url=database_url).database_url


@pytest.fixture(scope="session")
def postgres_engine(integration_database_url: str) -> Generator[Engine, None, None]:
    """Upgrade and connect to the dedicated real PostgreSQL test database."""
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "sqlalchemy.url",
        integration_database_url.replace("%", "%%"),
    )
    command.upgrade(alembic_config, "head")

    integration_engine = create_engine(integration_database_url, pool_pre_ping=True)
    try:
        yield integration_engine
    finally:
        integration_engine.dispose()


@pytest.fixture
def db_session(postgres_engine: Engine) -> Generator[Session, None, None]:
    """Isolate each test even when application services call commit()."""
    with postgres_engine.connect() as connection:
        outer_transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            outer_transaction.rollback()


@pytest.fixture
def db_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
