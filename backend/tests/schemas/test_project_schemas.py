"""Focused validation tests for project schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.project import ProjectCreate, ProjectUpdate


def test_project_create_trims_user_text() -> None:
    project = ProjectCreate(name="  Dining set  ", description="  Main room  ")

    assert project.name == "Dining set"
    assert project.description == "Main room"


@pytest.mark.parametrize("payload", [{}, {"name": None}])
def test_project_update_rejects_invalid_mutations(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate.model_validate(payload)
