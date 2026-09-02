"""Parametric plan persistence and draft mutation workflow."""

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.enums import PlanStatus
from app.models.furniture import Furniture
from app.models.furniture_component import FurnitureComponent
from app.models.furniture_plan import FurniturePlan
from app.schemas.plans import ComponentCreate, ComponentUpdate
from app.services._persistence import commit, commit_and_refresh
from app.services.dimensions import lock_dimensions_for_plan
from app.services.plan_geometry import generate_default_components
from app.services.plan_validation import validate_plan_components


class DraftPlanExistsError(RuntimeError):
    """Raised when a furniture item already has an editable draft."""


class PlanNotDraftError(RuntimeError):
    """Raised when a component mutation targets an immutable plan."""


class PlanRevisionSourceError(RuntimeError):
    """Raised when a draft is used as the source of a new revision."""


class PlanHistoryExistsError(RuntimeError):
    """Raised when initial generation is attempted after revision one."""


class FurnitureClassificationRequiredError(RuntimeError):
    """Raised when a plan is requested before furniture type is known."""


COMPONENT_COPY_FIELDS = (
    "component_name",
    "component_type",
    "width",
    "height",
    "depth",
    "thickness",
    "x",
    "y",
    "z",
    "rotation",
    "quantity",
    "sort_order",
)


def get_plan(session: Session, plan_id: UUID) -> FurniturePlan | None:
    statement = (
        select(FurniturePlan)
        .where(FurniturePlan.id == plan_id)
        .options(selectinload(FurniturePlan.components))
    )
    return session.scalar(statement)


def list_furniture_plans(
    session: Session,
    furniture_id: UUID,
) -> list[FurniturePlan]:
    statement = (
        select(FurniturePlan)
        .where(FurniturePlan.furniture_id == furniture_id)
        .options(selectinload(FurniturePlan.components))
        .order_by(FurniturePlan.revision.asc())
    )
    return list(session.scalars(statement).unique().all())


def get_draft_plan(
    session: Session,
    furniture_id: UUID,
) -> FurniturePlan | None:
    statement = select(FurniturePlan).where(
        FurniturePlan.furniture_id == furniture_id,
        FurniturePlan.status == PlanStatus.DRAFT,
    )
    return session.scalar(statement)


def create_initial_plan(session: Session, furniture: Furniture) -> FurniturePlan:
    """Generate a draft and lock overall dimensions in one transaction."""
    if furniture.furniture_type is None:
        raise FurnitureClassificationRequiredError(
            "Furniture classification is required before generating a 2D plan"
        )
    if get_draft_plan(session, furniture.id) is not None:
        raise DraftPlanExistsError("Furniture already has an editable draft plan")
    if session.scalar(
        select(FurniturePlan.id).where(
            FurniturePlan.furniture_id == furniture.id
        ).limit(1)
    ) is not None:
        raise PlanHistoryExistsError(
            "Furniture already has a plan; create a revision from a finalized plan"
        )

    try:
        dimensions = lock_dimensions_for_plan(session, furniture.id)
        latest_revision = session.scalar(
            select(func.max(FurniturePlan.revision)).where(
                FurniturePlan.furniture_id == furniture.id
            )
        )
        revision = 1 if latest_revision is None else latest_revision + 1
        plan = FurniturePlan(
            furniture_id=furniture.id,
            revision=revision,
            status=PlanStatus.DRAFT,
            furniture_type=furniture.furniture_type,
        )
        session.add(plan)
        session.flush()
        seeds = generate_default_components(
            furniture.furniture_type,
            width_mm=dimensions.width_mm,
            height_mm=dimensions.height_mm,
            depth_mm=dimensions.depth_mm,
        )
        session.add_all(
            FurnitureComponent(plan_id=plan.id, **asdict(seed))
            for seed in seeds
        )
        session.commit()
    except IntegrityError as exc:
        constraint_name = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(constraint_name, "constraint_name", None)
        session.rollback()
        if constraint_name in {
            "uq_furniture_plans_one_draft_per_furniture",
            "uq_furniture_plans_furniture_revision",
        }:
            raise DraftPlanExistsError(
                "Furniture already has an editable draft plan"
            ) from exc
        raise
    except Exception:
        session.rollback()
        raise

    created = get_plan(session, plan.id)
    if created is None:  # pragma: no cover - database invariant defense
        raise RuntimeError("Created plan could not be reloaded")
    return created


def finalize_plan(session: Session, plan: FurniturePlan) -> FurniturePlan:
    """Validate and permanently transition a draft to finalized."""
    require_draft(plan)
    validate_plan_components(plan.furniture_type, plan.components)
    plan.status = PlanStatus.FINALIZED
    _touch(plan)
    commit(session)
    finalized = get_plan(session, plan.id)
    if finalized is None:  # pragma: no cover - database invariant defense
        raise RuntimeError("Finalized plan could not be reloaded")
    return finalized


def create_revision(session: Session, source: FurniturePlan) -> FurniturePlan:
    """Copy a finalized design into the next editable revision."""
    if source.status != PlanStatus.FINALIZED:
        raise PlanRevisionSourceError(
            "Only a finalized plan can be used to create a revision"
        )
    if get_draft_plan(session, source.furniture_id) is not None:
        raise DraftPlanExistsError("Furniture already has an editable draft plan")

    try:
        latest_revision = session.scalar(
            select(func.max(FurniturePlan.revision)).where(
                FurniturePlan.furniture_id == source.furniture_id
            )
        )
        revision = 1 if latest_revision is None else latest_revision + 1
        plan = FurniturePlan(
            furniture_id=source.furniture_id,
            revision=revision,
            status=PlanStatus.DRAFT,
            furniture_type=source.furniture_type,
        )
        session.add(plan)
        session.flush()
        session.add_all(
            FurnitureComponent(
                plan_id=plan.id,
                **{
                    field: getattr(component, field)
                    for field in COMPONENT_COPY_FIELDS
                },
            )
            for component in source.components
        )
        session.commit()
    except IntegrityError as exc:
        constraint_name = getattr(getattr(exc, "orig", None), "diag", None)
        constraint_name = getattr(constraint_name, "constraint_name", None)
        session.rollback()
        if constraint_name in {
            "uq_furniture_plans_one_draft_per_furniture",
            "uq_furniture_plans_furniture_revision",
        }:
            raise DraftPlanExistsError(
                "Furniture already has an editable draft plan"
            ) from exc
        raise
    except Exception:
        session.rollback()
        raise

    created = get_plan(session, plan.id)
    if created is None:  # pragma: no cover - database invariant defense
        raise RuntimeError("Created revision could not be reloaded")
    return created


def require_draft(plan: FurniturePlan) -> None:
    if plan.status != PlanStatus.DRAFT:
        raise PlanNotDraftError("Finalized plans are immutable")


def _touch(plan: FurniturePlan) -> None:
    plan.updated_at = datetime.now(timezone.utc)


def get_component(
    session: Session,
    plan_id: UUID,
    component_id: UUID,
) -> FurnitureComponent | None:
    statement = select(FurnitureComponent).where(
        FurnitureComponent.id == component_id,
        FurnitureComponent.plan_id == plan_id,
    )
    return session.scalar(statement)


def add_component(
    session: Session,
    plan: FurniturePlan,
    payload: ComponentCreate,
) -> FurnitureComponent:
    require_draft(plan)
    component = FurnitureComponent(plan_id=plan.id, **payload.model_dump())
    session.add(component)
    _touch(plan)
    commit_and_refresh(session, component)
    return component


def update_component(
    session: Session,
    plan: FurniturePlan,
    component: FurnitureComponent,
    payload: ComponentUpdate,
) -> FurnitureComponent:
    require_draft(plan)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(component, field, value)
    _touch(plan)
    commit_and_refresh(session, component)
    return component


def delete_component(
    session: Session,
    plan: FurniturePlan,
    component: FurnitureComponent,
) -> None:
    require_draft(plan)
    session.delete(component)
    _touch(plan)
    commit(session)
