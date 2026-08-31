"""PostgreSQL-level constraints for canonical overall dimensions."""

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
    "overrides",
    [
        {"width_mm": "0"},
        {"unit": "ft"},
        {"source": "camera"},
        {"is_locked": True, "locked_at": None},
    ],
)
def test_postgresql_rejects_invalid_dimension_state(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    project = create_project(db_session, ProjectCreate(name="Dimension constraints"))
    furniture = create_furniture(
        db_session,
        project,
        FurnitureCreate(name="Chair", furniture_type="chair"),
    )
    values: dict[str, object] = {
        "id": str(uuid4()),
        "furniture_id": str(furniture.id),
        "width_mm": "600.0000",
        "height_mm": "900.0000",
        "depth_mm": "500.0000",
        "unit": "mm",
        "source": "manual",
        "is_locked": False,
        "locked_at": None,
    }
    values.update(overrides)
    statement = text(
        """
        INSERT INTO furniture_dimensions (
            id, furniture_id, width_mm, height_mm, depth_mm, unit, source,
            is_locked, locked_at
        ) VALUES (
            :id, :furniture_id, :width_mm, :height_mm, :depth_mm, :unit, :source,
            :is_locked, :locked_at
        )
        """
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(statement, values)
