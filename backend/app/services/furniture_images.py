"""Furniture image metadata and storage lifecycle operations."""

import logging
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.enums import FurnitureImageView, ImageInputSource
from app.models.furniture import Furniture
from app.models.furniture_image import FurnitureImage
from app.services._persistence import commit
from app.services.classification_state import invalidate_classification
from app.services.reconstruction_state import invalidate_reconstruction
from app.services.image_storage import ImageStorage
from app.services.image_validation import ValidatedImage

logger = logging.getLogger(__name__)
VIEW_ORDER = {view: position for position, view in enumerate(FurnitureImageView)}


class DuplicateFurnitureImageError(Exception):
    """Raised when a furniture item already has the requested view."""


def get_furniture_image(
    session: Session,
    furniture_id: UUID,
    view: FurnitureImageView,
) -> FurnitureImage | None:
    statement = select(FurnitureImage).where(
        FurnitureImage.furniture_id == furniture_id,
        FurnitureImage.view == view,
    )
    return session.scalar(statement)


def list_furniture_images(
    session: Session,
    furniture_id: UUID,
) -> list[FurnitureImage]:
    statement = select(FurnitureImage).where(
        FurnitureImage.furniture_id == furniture_id
    )
    images = list(session.scalars(statement).all())
    return sorted(images, key=lambda image: VIEW_ORDER[image.view])


def create_furniture_image(
    session: Session,
    storage: ImageStorage,
    furniture: Furniture,
    view: FurnitureImageView,
    source: ImageInputSource,
    original_filename: str,
    validated: ValidatedImage,
) -> FurnitureImage:
    storage_key = (
        f"{furniture.id}/{view.value}/{uuid4().hex}.{validated.extension}"
    )
    storage.save(storage_key, validated.data)
    image = FurnitureImage(
        furniture_id=furniture.id,
        view=view,
        source=source,
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=validated.content_type,
        file_size_bytes=validated.file_size_bytes,
        checksum_sha256=validated.checksum_sha256,
        pixel_width=validated.pixel_width,
        pixel_height=validated.pixel_height,
    )
    session.add(image)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        storage.delete(storage_key)
        raise DuplicateFurnitureImageError from exc
    except SQLAlchemyError:
        session.rollback()
        storage.delete(storage_key)
        raise
    session.refresh(image)
    return image


def update_furniture_image_calibration(
    session: Session,
    image: FurnitureImage,
    *,
    object_left_ratio: Decimal,
    object_top_ratio: Decimal,
    object_width_ratio: Decimal,
    object_height_ratio: Decimal,
    is_mirrored: bool,
) -> FurnitureImage:
    """Persist display calibration without changing source-image AI inputs."""
    image.object_left_ratio = object_left_ratio
    image.object_top_ratio = object_top_ratio
    image.object_width_ratio = object_width_ratio
    image.object_height_ratio = object_height_ratio
    image.is_mirrored = is_mirrored
    commit(session)
    session.refresh(image)
    return image


def delete_furniture_image(
    session: Session,
    storage: ImageStorage,
    image: FurnitureImage,
) -> None:
    storage_key = image.storage_key
    invalidate_classification(session, image.furniture_id)
    invalidate_reconstruction(session, image.furniture_id)
    session.delete(image)
    commit(session)
    delete_storage_objects(storage, [storage_key])


def storage_keys_for_furniture(session: Session, furniture_id: UUID) -> list[str]:
    statement = select(FurnitureImage.storage_key).where(
        FurnitureImage.furniture_id == furniture_id
    )
    return list(session.scalars(statement).all())


def storage_keys_for_project(session: Session, project_id: UUID) -> list[str]:
    statement = (
        select(FurnitureImage.storage_key)
        .join(Furniture, Furniture.id == FurnitureImage.furniture_id)
        .where(Furniture.project_id == project_id)
    )
    return list(session.scalars(statement).all())


def delete_storage_objects(storage: ImageStorage, storage_keys: list[str]) -> None:
    """Best-effort cleanup after the database has committed its deletion."""
    for storage_key in storage_keys:
        try:
            storage.delete(storage_key)
        except OSError:
            logger.exception("Could not remove orphaned image object %s", storage_key)
