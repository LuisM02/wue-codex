"""Shared pytest fixtures."""

import os
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import Callable
from uuid import uuid4

import psycopg2
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image
from psycopg2 import sql
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.api.dependencies import (
    get_furniture_classifier,
    get_furniture_reconstructor,
    get_image_storage,
)
from app.db.session import get_db_session
from app.main import app
from app.services.image_storage import LocalImageStorage

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_ai_configuration(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Tests must not invoke a live worker selected by the developer's .env."""
    monkeypatch.setenv("WUE_CLASSIFICATION_PROVIDER", "unconfigured")
    monkeypatch.setenv("WUE_RECONSTRUCTION_PROVIDER", "unconfigured")
    cached_dependencies = (get_settings, get_furniture_classifier, get_furniture_reconstructor)
    for dependency in cached_dependencies:
        dependency.cache_clear()
    try:
        yield
    finally:
        for dependency in cached_dependencies:
            dependency.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def integration_database_url() -> Generator[str, None, None]:
    """Create a disposable sibling database for one PostgreSQL test session."""
    configured_url = os.getenv("WUE_TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("WUE_TEST_DATABASE_URL is not configured")
    base_url = make_url(
        Settings(_env_file=None, database_url=configured_url).database_url
    )
    if not base_url.database or base_url.database in {"postgres", "template0", "template1"}:
        pytest.fail("WUE_TEST_DATABASE_URL must name a dedicated non-system database")

    database_name = (
        f"{base_url.database[:32]}_pytest_{os.getpid()}_{uuid4().hex[:8]}"
    )
    admin_connection = psycopg2.connect(
        dbname="postgres",
        host=base_url.host,
        port=base_url.port,
        user=base_url.username,
        password=base_url.password,
    )
    admin_connection.autocommit = True
    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )
        yield base_url.set(database=database_name).render_as_string(
            hide_password=False
        )
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(database_name)
                )
            )
        admin_connection.close()


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
def image_storage(tmp_path: Path) -> LocalImageStorage:
    return LocalImageStorage(tmp_path / "uploads")


@pytest.fixture
def db_client(
    db_session: Session,
    image_storage: LocalImageStorage,
) -> Generator[TestClient, None, None]:
    def override_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_image_storage] = lambda: image_storage
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def image_bytes_factory() -> Callable[..., bytes]:
    def make_image_bytes(
        image_format: str = "PNG",
        size: tuple[int, int] = (4, 3),
    ) -> bytes:
        output = BytesIO()
        Image.new("RGB", size, color=(120, 80, 40)).save(output, format=image_format)
        return output.getvalue()

    return make_image_bytes
