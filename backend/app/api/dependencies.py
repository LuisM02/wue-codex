"""Reusable FastAPI dependencies."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.classification import (
    FurnitureClassifier,
    UnconfiguredFurnitureClassifier,
)
from app.services.image_storage import LocalImageStorage


@lru_cache
def get_image_storage() -> LocalImageStorage:
    """Return the configured image storage implementation."""
    return LocalImageStorage(get_settings().upload_directory)


@lru_cache
def get_furniture_classifier() -> FurnitureClassifier:
    """Return the configured classifier adapter; unavailable by default."""
    return UnconfiguredFurnitureClassifier()
