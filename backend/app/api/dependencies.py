"""Reusable FastAPI dependencies."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.image_storage import LocalImageStorage


@lru_cache
def get_image_storage() -> LocalImageStorage:
    """Return the configured image storage implementation."""
    return LocalImageStorage(get_settings().upload_directory)
