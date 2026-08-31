"""Furniture CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.furniture import FurnitureCreate, FurnitureRead, FurnitureUpdate
from app.services import furniture as furniture_service
from app.services import projects as project_service

project_furniture_router = APIRouter(
    prefix="/projects/{project_id}/furniture",
    tags=["furniture"],
)
furniture_router = APIRouter(prefix="/furniture", tags=["furniture"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


@project_furniture_router.post(
    "",
    response_model=FurnitureRead,
    status_code=status.HTTP_201_CREATED,
)
def create_furniture(
    project_id: UUID,
    payload: FurnitureCreate,
    session: SessionDependency,
) -> FurnitureRead:
    project = project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return furniture_service.create_furniture(session, project, payload)


@project_furniture_router.get("", response_model=list[FurnitureRead])
def list_project_furniture(
    project_id: UUID,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[FurnitureRead]:
    project = project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return furniture_service.list_project_furniture(
        session,
        project_id,
        offset=offset,
        limit=limit,
    )


@furniture_router.get("/{furniture_id}", response_model=FurnitureRead)
def get_furniture(furniture_id: UUID, session: SessionDependency) -> FurnitureRead:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    return furniture


@furniture_router.patch("/{furniture_id}", response_model=FurnitureRead)
def update_furniture(
    furniture_id: UUID,
    payload: FurnitureUpdate,
    session: SessionDependency,
) -> FurnitureRead:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    return furniture_service.update_furniture(session, furniture, payload)


@furniture_router.delete("/{furniture_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_furniture(furniture_id: UUID, session: SessionDependency) -> Response:
    furniture = furniture_service.get_furniture(session, furniture_id)
    if furniture is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture not found")
    furniture_service.delete_furniture(session, furniture)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
