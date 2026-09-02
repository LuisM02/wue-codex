"""PostgreSQL-level constraints for plans and component geometry."""

from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas.dimensions import FurnitureDimensionsWrite
from app.schemas.furniture import FurnitureCreate
from app.schemas.project import ProjectCreate
from app.models.furniture_component import FurnitureComponent
from app.models.furniture_plan import FurniturePlan
from app.services import plans as plan_service
from app.services.dimensions import get_dimensions, set_dimensions
from app.services.furniture import create_furniture
from app.services.projects import create_project
from tests.support.photo_reconstruction import seed_test_reconstruction

pytestmark = pytest.mark.integration


def create_furniture_record(session: Session):
    project = create_project(session, ProjectCreate(name="Plan constraints"))
    return create_furniture(
        session,
        project,
        FurnitureCreate(name="Chair", furniture_type="chair"),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"revision": 0},
        {"status": "archived"},
        {"furniture_type": "bed"},
    ],
)
def test_postgresql_rejects_invalid_plan_state(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    furniture = create_furniture_record(db_session)
    values: dict[str, object] = {
        "id": str(uuid4()),
        "furniture_id": str(furniture.id),
        "revision": 1,
        "status": "draft",
        "furniture_type": "chair",
    }
    values.update(overrides)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO furniture_plans (
                        id, furniture_id, revision, status, furniture_type
                    ) VALUES (
                        :id, :furniture_id, :revision, :status, :furniture_type
                    )
                    """
                ),
                values,
            )


def create_plan_record(session: Session):
    furniture = create_furniture_record(session)
    dimensions, _ = set_dimensions(
        session,
        furniture,
        FurnitureDimensionsWrite(
            width="1000",
            height="1200",
            depth="600",
            unit="mm",
        ),
    )
    seed_test_reconstruction(session, furniture, dimensions)
    return plan_service.create_initial_plan(session, furniture)


@pytest.mark.parametrize(
    "overrides",
    [
        {"component_type": "brace"},
        {"width": "0"},
        {"height": "0"},
        {"depth": "0"},
        {"thickness": "0"},
        {"quantity": 0},
        {"sort_order": -1},
    ],
)
def test_postgresql_rejects_invalid_component_geometry(
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    plan = create_plan_record(db_session)
    values: dict[str, object] = {
        "id": str(uuid4()),
        "plan_id": str(plan.id),
        "component_name": "custom",
        "component_type": "panel",
        "width": "100.0000",
        "height": "20.0000",
        "depth": "30.0000",
        "thickness": "20.0000",
        "x": "0",
        "y": "0",
        "z": "0",
        "rotation": "0",
        "quantity": 1,
        "sort_order": 10,
    }
    values.update(overrides)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO furniture_components (
                        id, plan_id, component_name, component_type, width,
                        height, depth, thickness, x, y, z, rotation, quantity,
                        sort_order
                    ) VALUES (
                        :id, :plan_id, :component_name, :component_type, :width,
                        :height, :depth, :thickness, :x, :y, :z, :rotation,
                        :quantity, :sort_order
                    )
                    """
                ),
                values,
            )


def test_postgresql_allows_only_one_draft_per_furniture(
    db_session: Session,
) -> None:
    plan = create_plan_record(db_session)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO furniture_plans (
                        id, furniture_id, revision, status, furniture_type
                    ) VALUES (
                        :id, :furniture_id, 2, 'draft', 'chair'
                    )
                    """
                ),
                {"id": str(uuid4()), "furniture_id": str(plan.furniture_id)},
            )


def test_generation_failure_rolls_back_the_dimension_lock(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    furniture = create_furniture_record(db_session)
    dimensions, _ = set_dimensions(
        db_session,
        furniture,
        FurnitureDimensionsWrite(
            width="1000",
            height="1200",
            depth="600",
            unit="mm",
        ),
    )
    seed_test_reconstruction(db_session, furniture, dimensions)

    real_lock = plan_service.lock_dimensions_for_plan

    def fail_after_lock(*args: object, **kwargs: object) -> None:
        real_lock(*args, **kwargs)
        raise RuntimeError("synthetic geometry failure")

    monkeypatch.setattr(plan_service, "lock_dimensions_for_plan", fail_after_lock)

    with pytest.raises(RuntimeError, match="synthetic geometry failure"):
        plan_service.create_initial_plan(db_session, furniture)

    db_session.expire_all()
    dimensions = get_dimensions(db_session, furniture.id)
    assert dimensions is not None
    assert dimensions.is_locked is False
    assert dimensions.locked_at is None
    assert plan_service.list_furniture_plans(db_session, furniture.id) == []


def test_deleting_furniture_cascades_to_plans_and_components(
    db_session: Session,
) -> None:
    plan = create_plan_record(db_session)
    plan_id = plan.id
    furniture = plan.furniture
    component_count = db_session.scalar(
        select(func.count()).select_from(FurnitureComponent).where(
            FurnitureComponent.plan_id == plan_id
        )
    )
    assert component_count == 6

    db_session.delete(furniture)
    db_session.commit()

    assert db_session.get(FurniturePlan, plan_id) is None
    assert db_session.scalar(
        select(func.count()).select_from(FurnitureComponent).where(
            FurnitureComponent.plan_id == plan_id
        )
    ) == 0
