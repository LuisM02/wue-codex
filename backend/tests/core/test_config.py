"""Tests for typed application configuration."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_postgresql_psycopg2_url() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg2://user:pass@db.example/wue",
        api_v1_prefix="/custom/v1/",
        environment="test",
    )

    assert settings.database_url.endswith("/wue")
    assert settings.api_v1_prefix == "/custom/v1"
    assert settings.environment == "test"


def test_settings_reject_non_postgresql_database() -> None:
    with pytest.raises(ValidationError, match="must use PostgreSQL"):
        Settings(_env_file=None, database_url="sqlite:///wue.db")


@pytest.mark.parametrize("prefix", ["api/v1", "/", ""])
def test_settings_reject_invalid_api_prefix(prefix: str) -> None:
    with pytest.raises(ValidationError, match="non-root absolute path"):
        Settings(_env_file=None, api_v1_prefix=prefix)
