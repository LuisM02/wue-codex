"""Reusable FastAPI dependencies."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.classification import (
    FurnitureClassifier,
    UnconfiguredFurnitureClassifier,
)
from app.services.image_storage import LocalImageStorage
from app.services.http_reconstruction import HttpFurnitureReconstructor
from app.services.http_classification import HttpFurnitureClassifier
from app.services.photo_reconstruction import (
    FurnitureReconstructor,
    UnconfiguredFurnitureReconstructor,
)


@lru_cache
def get_image_storage() -> LocalImageStorage:
    """Return the configured image storage implementation."""
    return LocalImageStorage(get_settings().upload_directory)


@lru_cache
def get_furniture_classifier() -> FurnitureClassifier:
    """Return the configured five-view recognition adapter."""
    settings = get_settings()
    if settings.classification_provider == "http":
        return HttpFurnitureClassifier(
            settings.classification_service_url,
            settings.classification_timeout_seconds,
        )
    return UnconfiguredFurnitureClassifier()


@lru_cache
def get_furniture_reconstructor() -> FurnitureReconstructor:
    """Return the configured multi-view reconstruction adapter."""
    settings = get_settings()
    if settings.reconstruction_provider == "http":
        return HttpFurnitureReconstructor(
            settings.reconstruction_service_url,
            settings.reconstruction_timeout_seconds,
        )
    return UnconfiguredFurnitureReconstructor()
