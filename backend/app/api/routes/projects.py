"""Project CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_image_storage
from app.db.session import get_db_session
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import projects as project_service
from app.services.image_storage import LocalImageStorage

router = APIRouter(prefix="/projects", tags=["projects"])
SessionDependency = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[LocalImageStorage, Depends(get_image_storage)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: SessionDependency) -> ProjectRead:
    return project_service.create_project(session, payload)


@router.get("", response_model=list[ProjectRead])
def list_projects(
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProjectRead]:
    return project_service.list_projects(session, offset=offset, limit=limit)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, session: SessionDependency) -> ProjectRead:
    project = project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    session: SessionDependency,
) -> ProjectRead:
    project = project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project_service.update_project(session, project, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    session: SessionDependency,
    storage: StorageDependency,
) -> Response:
    project = project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    project_service.delete_project(session, project, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
