"""Small transaction helpers shared by persistence services."""

from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def commit_and_refresh(session: Session, instance: Any) -> None:
    """Commit a mutation, roll back failures, and refresh server values."""
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    session.refresh(instance)


def commit(session: Session) -> None:
    """Commit a mutation and leave the session usable after failures."""
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
