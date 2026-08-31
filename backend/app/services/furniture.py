"""Furniture persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.furniture import Furniture
from app.models.project import Project
from app.schemas.furniture import FurnitureCreate, FurnitureUpdate
from app.services.classification_state import invalidate_classification
from app.services import furniture_images as image_service
from app.services._persistence import commit, commit_and_refresh
from app.services.image_storage import ImageStorage


def create_furniture(
    session: Session,
    project: Project,
    payload: FurnitureCreate,
) -> Furniture:
    furniture = Furniture(project_id=project.id, **payload.model_dump())
    session.add(furniture)
    commit_and_refresh(session, furniture)
    return furniture


def list_project_furniture(
    session: Session,
    project_id: UUID,
    *,
    offset: int,
    limit: int,
) -> list[Furniture]:
    statement = (
        select(Furniture)
        .where(Furniture.project_id == project_id)
        .order_by(Furniture.created_at.asc(), Furniture.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def get_furniture(session: Session, furniture_id: UUID) -> Furniture | None:
    return session.get(Furniture, furniture_id)


def update_furniture(
    session: Session,
    furniture: Furniture,
    payload: FurnitureUpdate,
) -> Furniture:
    updates = payload.model_dump(exclude_unset=True)
    requested_type = updates.get("furniture_type")
    if requested_type is not None and requested_type != furniture.furniture_type:
        invalidate_classification(session, furniture.id)
    for field, value in updates.items():
        setattr(furniture, field, value)
    commit_and_refresh(session, furniture)
    return furniture


def delete_furniture(
    session: Session,
    furniture: Furniture,
    storage: ImageStorage,
) -> None:
    storage_keys = image_service.storage_keys_for_furniture(session, furniture.id)
    session.delete(furniture)
    commit(session)
    image_service.delete_storage_objects(storage, storage_keys)
