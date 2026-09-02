"""Database-level regression tests for the furniture type boundary."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas.project import ProjectCreate
from app.services.projects import create_project

pytestmark = pytest.mark.integration


def test_postgresql_rejects_out_of_scope_furniture_type(
    db_session: Session,
) -> None:
    project = create_project(db_session, ProjectCreate(name="Constraint test"))
    statement = text(
        """
        INSERT INTO furniture (id, project_id, name, furniture_type)
        VALUES (:id, :project_id, :name, :furniture_type)
        """
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                statement,
                {
                    "id": str(uuid4()),
                    "project_id": str(project.id),
                    "name": "Invalid bed",
                    "furniture_type": "bed",
                },
            )


def test_postgresql_allows_type_to_await_classification(
    db_session: Session,
) -> None:
    project = create_project(db_session, ProjectCreate(name="Unclassified test"))

    db_session.execute(
        text(
            """
            INSERT INTO furniture (id, project_id, name, furniture_type)
            VALUES (:id, :project_id, :name, NULL)
            """
        ),
        {
            "id": str(uuid4()),
            "project_id": str(project.id),
            "name": "Awaiting classification",
        },
    )
    db_session.flush()
