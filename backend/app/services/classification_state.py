"""Small persistence helpers for classification state invalidation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.furniture_classification import FurnitureClassification


def get_classification(
    session: Session,
    furniture_id: UUID,
) -> FurnitureClassification | None:
    statement = select(FurnitureClassification).where(
        FurnitureClassification.furniture_id == furniture_id
    )
    return session.scalar(statement)


def invalidate_classification(session: Session, furniture_id: UUID) -> None:
    classification = get_classification(session, furniture_id)
    if classification is not None:
        session.delete(classification)
