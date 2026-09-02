"""Photo-derived part reconstruction endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_furniture_reconstructor, get_image_storage
from app.db.session import get_db_session
from app.schemas.photo_reconstruction import FurnitureReconstructionRead
from app.services import furniture as furniture_service
from app.services import photo_reconstruction as reconstruction_service
from app.services.image_storage import LocalImageStorage
from app.services.reconstruction_state import get_reconstruction

router = APIRouter(
    prefix="/furniture/{furniture_id}/reconstruction",
    tags=["photo-reconstruction"],
)
SessionDependency = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[LocalImageStorage, Depends(get_image_storage)]
ReconstructorDependency = Annotated[
    reconstruction_service.FurnitureReconstructor,
    Depends(get_furniture_reconstructor),
]


@router.post("", response_model=FurnitureReconstructionRead)
def reconstruct_furniture(
    furniture_id: UUID,
    session: SessionDependency,
    storage: StorageDependency,
    reconstructor: ReconstructorDependency,
) -> FurnitureReconstructionRead:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    try:
        return reconstruction_service.reconstruct_furniture(
            session, storage, reconstructor, furniture
        )
    except reconstruction_service.ReconstructionPrerequisiteError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except reconstruction_service.ReconstructionProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except reconstruction_service.InvalidReconstructionOutputError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("", response_model=FurnitureReconstructionRead)
def read_reconstruction(
    furniture_id: UUID,
    session: SessionDependency,
) -> FurnitureReconstructionRead:
    if furniture_service.get_furniture(session, furniture_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    reconstruction = get_reconstruction(session, furniture_id)
    if reconstruction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo reconstruction not found",
        )
    return reconstruction
