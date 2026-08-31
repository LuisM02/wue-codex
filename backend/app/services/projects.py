"""Project persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services._persistence import commit, commit_and_refresh


def create_project(session: Session, payload: ProjectCreate) -> Project:
    project = Project(**payload.model_dump())
    session.add(project)
    commit_and_refresh(session, project)
    return project


def list_projects(session: Session, *, offset: int, limit: int) -> list[Project]:
    statement = (
        select(Project)
        .order_by(Project.created_at.asc(), Project.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def get_project(session: Session, project_id: UUID) -> Project | None:
    return session.get(Project, project_id)


def update_project(
    session: Session,
    project: Project,
    payload: ProjectUpdate,
) -> Project:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    commit_and_refresh(session, project)
    return project


def delete_project(session: Session, project: Project) -> None:
    session.delete(project)
    commit(session)
