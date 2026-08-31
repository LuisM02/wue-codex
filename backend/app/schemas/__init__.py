"""Pydantic request and response schema exports."""

from app.schemas.classification import FurnitureClassificationRead
from app.schemas.furniture import FurnitureCreate, FurnitureRead, FurnitureUpdate
from app.schemas.furniture_image import FurnitureImageRead
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

__all__ = [
    "FurnitureClassificationRead",
    "FurnitureCreate",
    "FurnitureImageRead",
    "FurnitureRead",
    "FurnitureUpdate",
    "ProjectCreate",
    "ProjectRead",
    "ProjectUpdate",
]
