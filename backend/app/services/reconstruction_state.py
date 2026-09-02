"""Persistence helpers for invalidating photo-derived reconstruction state."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.furniture_reconstruction import FurnitureReconstruction


def get_reconstruction(
    session: Session,
    furniture_id: UUID,
) -> FurnitureReconstruction | None:
    statement = (
        select(FurnitureReconstruction)
        .where(FurnitureReconstruction.furniture_id == furniture_id)
        .options(selectinload(FurnitureReconstruction.parts))
    )
    return session.scalar(statement)


def invalidate_reconstruction(session: Session, furniture_id: UUID) -> None:
    reconstruction = get_reconstruction(session, furniture_id)
    if reconstruction is not None:
        session.delete(reconstruction)
