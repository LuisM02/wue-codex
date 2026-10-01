"""Five-view furniture image upload, metadata, content, and deletion APIs."""

from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_image_storage
from app.core.config import Settings, get_settings
from app.core.enums import FurnitureImageView, ImageInputSource
from app.db.session import get_db_session
from app.models.furniture import Furniture
from app.models.furniture_image import FurnitureImage
from app.schemas.furniture_image import (
    FurnitureImageCalibrationUpdate,
    FurnitureImageRead,
)
from app.services import furniture as furniture_service
from app.services import furniture_images as image_service
from app.services.image_storage import (
    ImageStorageNotFoundError,
    LocalImageStorage,
)
from app.services.image_validation import (
    ImageSizeLimitError,
    ImageValidationError,
    safe_original_filename,
    validate_image,
)

router = APIRouter(
    prefix="/furniture/{furniture_id}/images",
    tags=["furniture-images"],
)
SessionDependency = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[LocalImageStorage, Depends(get_image_storage)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def require_furniture(session: Session, furniture_id: UUID) -> Furniture:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    return furniture


def require_image(
    session: Session,
    furniture_id: UUID,
    view: FurnitureImageView,
) -> FurnitureImage:
    require_furniture(session, furniture_id)
    image = image_service.get_furniture_image(session, furniture_id, view)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Furniture image not found",
        )
    return image


@router.post(
    "/{view}",
    response_model=FurnitureImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_furniture_image(
    furniture_id: UUID,
    view: FurnitureImageView,
    session: SessionDependency,
    storage: StorageDependency,
    settings: SettingsDependency,
    file: Annotated[UploadFile, File()],
    source: Annotated[ImageInputSource, Form()] = ImageInputSource.UPLOAD,
) -> FurnitureImageRead:
    furniture = require_furniture(session, furniture_id)
    if image_service.get_furniture_image(session, furniture_id, view) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Furniture image view already exists",
        )

    try:
        data = await file.read(settings.max_image_bytes + 1)
    finally:
        await file.close()

    try:
        validated = validate_image(
            data,
            file.content_type,
            max_bytes=settings.max_image_bytes,
            max_pixels=settings.max_image_pixels,
        )
        return image_service.create_furniture_image(
            session,
            storage,
            furniture,
            view,
            source,
            safe_original_filename(file.filename),
            validated,
        )
    except ImageSizeLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except image_service.DuplicateFurnitureImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Furniture image view already exists",
        ) from exc


@router.get("", response_model=list[FurnitureImageRead])
def list_furniture_images(
    furniture_id: UUID,
    session: SessionDependency,
) -> list[FurnitureImageRead]:
    require_furniture(session, furniture_id)
    return image_service.list_furniture_images(session, furniture_id)


@router.get("/{view}", response_model=FurnitureImageRead)
def get_furniture_image(
    furniture_id: UUID,
    view: FurnitureImageView,
    session: SessionDependency,
) -> FurnitureImageRead:
    return require_image(session, furniture_id, view)


@router.put("/{view}/calibration", response_model=FurnitureImageRead)
def update_furniture_image_calibration(
    furniture_id: UUID,
    view: FurnitureImageView,
    payload: FurnitureImageCalibrationUpdate,
    session: SessionDependency,
) -> FurnitureImageRead:
    image = require_image(session, furniture_id, view)
    return image_service.update_furniture_image_calibration(
        session,
        image,
        object_left_ratio=payload.object_left_ratio,
        object_top_ratio=payload.object_top_ratio,
        object_width_ratio=payload.object_width_ratio,
        object_height_ratio=payload.object_height_ratio,
        is_mirrored=payload.is_mirrored,
    )


@router.get("/{view}/content", response_class=Response)
def get_furniture_image_content(
    furniture_id: UUID,
    view: FurnitureImageView,
    session: SessionDependency,
    storage: StorageDependency,
) -> Response:
    image = require_image(session, furniture_id, view)
    try:
        content = storage.read(image.storage_key)
    except ImageStorageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Furniture image content not found",
        ) from exc

    encoded_filename = quote(image.original_filename)
    return Response(
        content=content,
        media_type=image.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            "ETag": f'"{image.checksum_sha256}"',
        },
    )


@router.delete("/{view}", status_code=status.HTTP_204_NO_CONTENT)
def delete_furniture_image(
    furniture_id: UUID,
    view: FurnitureImageView,
    session: SessionDependency,
    storage: StorageDependency,
) -> Response:
    image = require_image(session, furniture_id, view)
    image_service.delete_furniture_image(session, storage, image)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
