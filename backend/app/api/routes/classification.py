"""Furniture classification endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_furniture_classifier, get_image_storage
from app.db.session import get_db_session
from app.models.furniture import Furniture
from app.schemas.classification import FurnitureClassificationRead
from app.services import classification as classification_service
from app.services import furniture as furniture_service
from app.services.image_storage import LocalImageStorage

router = APIRouter(
    prefix="/furniture/{furniture_id}/classification",
    tags=["classification"],
)
SessionDependency = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[LocalImageStorage, Depends(get_image_storage)]
ClassifierDependency = Annotated[
    classification_service.FurnitureClassifier,
    Depends(get_furniture_classifier),
]


def require_furniture(session: Session, furniture_id: UUID) -> Furniture:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    return furniture


@router.post("", response_model=FurnitureClassificationRead)
def classify_furniture(
    furniture_id: UUID,
    session: SessionDependency,
    storage: StorageDependency,
    classifier: ClassifierDependency,
) -> FurnitureClassificationRead:
    furniture = require_furniture(session, furniture_id)
    try:
        return classification_service.classify_furniture(
            session,
            storage,
            classifier,
            furniture,
        )
    except classification_service.ClassificationPrerequisiteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except classification_service.ClassificationInputRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except classification_service.ClassifierUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except classification_service.InvalidClassifierOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=FurnitureClassificationRead)
def get_furniture_classification(
    furniture_id: UUID,
    session: SessionDependency,
) -> FurnitureClassificationRead:
    require_furniture(session, furniture_id)
    classification = classification_service.get_classification(session, furniture_id)
    if classification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Furniture classification not found",
        )
    return classification
