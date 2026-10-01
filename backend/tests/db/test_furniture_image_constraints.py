"""PostgreSQL-level constraints for image workflow metadata."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas.furniture import FurnitureCreate
from app.schemas.project import ProjectCreate
from app.services.furniture import create_furniture
from app.services.projects import create_project

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("column", "invalid_value"),
    [
        ("view", "bottom"),
        ("source", "ai_generated"),
        ("content_type", "image/gif"),
    ],
)
def test_postgresql_rejects_invalid_image_metadata_values(
    db_session: Session,
    column: str,
    invalid_value: str,
) -> None:
    project = create_project(db_session, ProjectCreate(name="Image constraints"))
    furniture = create_furniture(
        db_session,
        project,
        FurnitureCreate(name="Chair", furniture_type="chair"),
    )
    values = {
        "id": str(uuid4()),
        "furniture_id": str(furniture.id),
        "view": "front",
        "source": "upload",
        "storage_key": f"test/{uuid4()}.png",
        "original_filename": "test.png",
        "content_type": "image/png",
        "file_size_bytes": 100,
        "checksum_sha256": "a" * 64,
        "pixel_width": 10,
        "pixel_height": 10,
    }
    values[column] = invalid_value
    statement = text(
        """
        INSERT INTO furniture_images (
            id, furniture_id, view, source, storage_key, original_filename,
            content_type, file_size_bytes, checksum_sha256, pixel_width, pixel_height
        ) VALUES (
            :id, :furniture_id, :view, :source, :storage_key, :original_filename,
            :content_type, :file_size_bytes, :checksum_sha256, :pixel_width, :pixel_height
        )
        """
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(statement, values)


@pytest.mark.parametrize(
    ("left", "top", "width", "height"),
    [
        (-0.1, 0, 0.5, 1),
        (0, -0.1, 1, 0.5),
        (0, 0, 0, 1),
        (0, 0, 1, 0),
        (0.6, 0, 0.5, 1),
        (0, 0.6, 1, 0.5),
    ],
)
def test_postgresql_rejects_invalid_image_calibration(
    db_session: Session,
    left: float,
    top: float,
    width: float,
    height: float,
) -> None:
    project = create_project(db_session, ProjectCreate(name="Calibration constraints"))
    furniture = create_furniture(
        db_session,
        project,
        FurnitureCreate(name="Chair", furniture_type="chair"),
    )
    statement = text(
        """
        INSERT INTO furniture_images (
            id, furniture_id, view, source, storage_key, original_filename,
            content_type, file_size_bytes, checksum_sha256, pixel_width, pixel_height,
            object_left_ratio, object_top_ratio, object_width_ratio, object_height_ratio,
            is_mirrored
        ) VALUES (
            :id, :furniture_id, 'front', 'upload', :storage_key, 'test.png',
            'image/png', 100, :checksum, 10, 10, :left, :top, :width, :height, false
        )
        """
    )
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                statement,
                {
                    "id": str(uuid4()),
                    "furniture_id": str(furniture.id),
                    "storage_key": f"test/{uuid4()}.png",
                    "checksum": "a" * 64,
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                },
            )
