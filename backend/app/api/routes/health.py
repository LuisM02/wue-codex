"""Service and database health endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.health import DatabaseHealth, ServiceHealth

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=ServiceHealth)
def service_health(request: Request) -> ServiceHealth:
    """Report API availability without requiring the database."""
    settings = request.app.state.settings
    return ServiceHealth(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/health/database",
    response_model=DatabaseHealth,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable"}},
)
def database_health(session: Session = Depends(get_db_session)) -> DatabaseHealth:
    """Verify that PostgreSQL accepts a trivial read-only query."""
    try:
        result = session.execute(text("SELECT 1"))
        if result.scalar_one() != 1:
            raise SQLAlchemyError("Unexpected database health-check result")
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc

    return DatabaseHealth(status="ok", database="reachable")
