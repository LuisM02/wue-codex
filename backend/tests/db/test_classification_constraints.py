"""PostgreSQL-level constraints for persisted classifier output."""

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
    ("predicted_type", "confidence"),
    [("bed", "0.5000"), ("chair", "-0.0001"), ("chair", "1.0001")],
)
def test_postgresql_rejects_invalid_classification_values(
    db_session: Session,
    predicted_type: str,
    confidence: str,
) -> None:
    project = create_project(db_session, ProjectCreate(name="Classifier constraints"))
    furniture = create_furniture(
        db_session,
        project,
        FurnitureCreate(name="Chair", furniture_type="chair"),
    )
    statement = text(
        """
        INSERT INTO furniture_classifications (
            id, furniture_id, predicted_type, confidence, classifier_name,
            classifier_version, input_signature
        ) VALUES (
            :id, :furniture_id, :predicted_type, :confidence, :classifier_name,
            :classifier_version, :input_signature
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
                    "predicted_type": predicted_type,
                    "confidence": confidence,
                    "classifier_name": "invalid-test",
                    "classifier_version": None,
                    "input_signature": "a" * 64,
                },
            )
