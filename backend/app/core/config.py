"""Typed environment configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """Runtime settings loaded from WUE-prefixed environment values."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="WUE_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "WUE API"
    app_version: str = "0.8.0"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/wue_codex_db"
    )
    upload_directory: Path = Path("uploads")
    max_image_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_image_pixels: int = Field(default=40_000_000, gt=0)

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or normalized == "":
            raise ValueError("api_v1_prefix must be a non-root absolute path")
        return normalized

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        try:
            url = make_url(value)
        except ArgumentError as exc:
            raise ValueError("database_url must be a valid SQLAlchemy URL") from exc

        if url.get_backend_name() != "postgresql":
            raise ValueError("database_url must use PostgreSQL")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""
    return Settings()
