"""Manual-first overall furniture dimension endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.furniture import Furniture
from app.schemas.dimensions import FurnitureDimensionsRead, FurnitureDimensionsWrite
from app.services import dimensions as dimension_service
from app.services import furniture as furniture_service

router = APIRouter(
    prefix="/furniture/{furniture_id}/dimensions",
    tags=["dimensions"],
)
SessionDependency = Annotated[Session, Depends(get_db_session)]


def require_furniture(session: Session, furniture_id: UUID) -> Furniture:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    return furniture


@router.put("", response_model=FurnitureDimensionsRead)
def set_furniture_dimensions(
    furniture_id: UUID,
    payload: FurnitureDimensionsWrite,
    response: Response,
    session: SessionDependency,
) -> FurnitureDimensionsRead:
    furniture = require_furniture(session, furniture_id)
    try:
        dimensions, created = dimension_service.set_dimensions(
            session,
            furniture,
            payload,
        )
    except dimension_service.DimensionsLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except dimension_service.ManualDimensionsConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except dimension_service.DimensionRangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return dimensions


@router.get("", response_model=FurnitureDimensionsRead)
def get_furniture_dimensions(
    furniture_id: UUID,
    session: SessionDependency,
) -> FurnitureDimensionsRead:
    require_furniture(session, furniture_id)
    dimensions = dimension_service.get_dimensions(session, furniture_id)
    if dimensions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Furniture dimensions not found",
        )
    return dimensions


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_furniture_dimensions(
    furniture_id: UUID,
    session: SessionDependency,
) -> Response:
    require_furniture(session, furniture_id)
    dimensions = dimension_service.get_dimensions(session, furniture_id)
    if dimensions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Furniture dimensions not found",
        )
    try:
        dimension_service.delete_dimensions(session, dimensions)
    except dimension_service.DimensionsLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
