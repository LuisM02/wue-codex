"""Parametric plan persistence and draft mutation workflow."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.enums import PlanStatus
from app.models.furniture import Furniture
from app.models.furniture_component import FurnitureComponent
from app.models.furniture_plan import FurniturePlan
from app.models.furniture_reconstruction import FurnitureReconstruction
from app.schemas.plans import ComponentCreate, ComponentUpdate
from app.services import dimensions as dimension_service
from app.services._persistence import commit, commit_and_refresh
from app.services.dimensions import lock_dimensions_for_plan
from app.services.plan_validation import validate_plan_components
from app.services.reconstruction_state import get_reconstruction
from app.services.plan_geometry import MIN_PLAN_DIMENSION_MM, PlanGeometryRangeError


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


class PhotoReconstructionRequiredError(RuntimeError):
    """Raised instead of silently substituting generic furniture geometry."""


class PlanPartsReviewRequiredError(RuntimeError):
    """Raised when photo-derived parts have not been accepted by the user."""


class ComponentGeometryValidationError(ValueError):
    """Raised when a merged draft component would contain invalid geometry."""


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
    "rotation_x",
    "rotation_y",
    "rotation_z",
    "geometry_kind",
    "profile_points",
    "source_confidence",
    "source_views",
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


def _add_reconstruction_components(
    session: Session,
    plan: FurniturePlan,
    reconstruction: FurnitureReconstruction,
) -> None:
    session.add_all(
        FurnitureComponent(
            plan_id=plan.id,
            source_reconstruction_part_id=part.id,
            component_name=part.component_name,
            component_type=part.component_type,
            width=part.width,
            height=part.height,
            depth=part.depth,
            thickness=None,
            x=part.x,
            y=part.y,
            z=part.z,
            rotation=part.rotation_y,
            rotation_x=part.rotation_x,
            rotation_y=part.rotation_y,
            rotation_z=part.rotation_z,
            geometry_kind=part.geometry_kind,
            profile_points=part.profile_points,
            source_confidence=part.confidence,
            source_views=part.source_views,
            quantity=part.quantity,
            sort_order=part.sort_order,
        )
        for part in reconstruction.parts
    )


def create_initial_plan(session: Session, furniture: Furniture) -> FurniturePlan:
    """Create a draft only from a validated photo-derived reconstruction."""
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
    dimensions = dimension_service.get_dimensions(session, furniture.id)
    if dimensions is None:
        raise dimension_service.DimensionsRequiredError(
            "Overall dimensions are required before generating a 2D plan"
        )
    if min(dimensions.width_mm, dimensions.height_mm, dimensions.depth_mm) < MIN_PLAN_DIMENSION_MM:
        raise PlanGeometryRangeError(
            "Overall width, height, and depth must each be at least "
            f"{MIN_PLAN_DIMENSION_MM} millimeter for 2D generation"
        )
    reconstruction = get_reconstruction(session, furniture.id)
    if reconstruction is None:
        raise PhotoReconstructionRequiredError(
            "Photo-derived part reconstruction is required before generating a 2D plan; "
            "WUE will not use a generic furniture template"
        )
    if reconstruction.furniture_type != furniture.furniture_type:
        raise PhotoReconstructionRequiredError(
            "The saved reconstruction does not match the current furniture type; analyze the photos again"
        )
    if not reconstruction.parts:
        raise PhotoReconstructionRequiredError(
            "The saved reconstruction contains no detected parts; analyze the photos again"
        )

    try:
        lock_dimensions_for_plan(session, furniture.id)
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
            source_reconstruction_id=reconstruction.id,
        )
        session.add(plan)
        session.flush()
        _add_reconstruction_components(session, plan, reconstruction)
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
    if plan.source_reconstruction_id is not None and plan.parts_reviewed_at is None:
        raise PlanPartsReviewRequiredError(
            "Review and confirm the AI-detected parts before finalizing the 2D plan"
        )
    validate_plan_components(plan.furniture_type, plan.components)
    plan.status = PlanStatus.FINALIZED
    _touch(plan)
    commit(session)
    finalized = get_plan(session, plan.id)
    if finalized is None:  # pragma: no cover - database invariant defense
        raise RuntimeError("Finalized plan could not be reloaded")
    return finalized


def review_plan_parts(session: Session, plan: FurniturePlan) -> FurniturePlan:
    """Record the user's approval of the editable AI part proposal."""
    require_draft(plan)
    plan.parts_reviewed_at = datetime.now(timezone.utc)
    _touch(plan)
    commit(session)
    reviewed = get_plan(session, plan.id)
    if reviewed is None:  # pragma: no cover - database invariant defense
        raise RuntimeError("Reviewed plan could not be reloaded")
    return reviewed


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
            source_reconstruction_id=source.source_reconstruction_id,
            parts_reviewed_at=datetime.now(timezone.utc),
        )
        session.add(plan)
        session.flush()
        session.add_all(
            FurnitureComponent(
                plan_id=plan.id,
                source_reconstruction_part_id=component.source_reconstruction_part_id,
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


def create_reconstruction_revision(
    session: Session,
    source: FurniturePlan,
) -> FurniturePlan:
    """Create the next draft from the latest photo analysis, preserving history."""
    if source.status != PlanStatus.FINALIZED:
        raise PlanRevisionSourceError(
            "Only a finalized plan can be rebuilt from photos"
        )
    if get_draft_plan(session, source.furniture_id) is not None:
        raise DraftPlanExistsError("Furniture already has an editable draft plan")
    reconstruction = get_reconstruction(session, source.furniture_id)
    if reconstruction is None or not reconstruction.parts:
        raise PhotoReconstructionRequiredError(
            "Analyze the five photos before rebuilding the 2D plan"
        )
    if reconstruction.furniture_type != source.furniture_type:
        raise PhotoReconstructionRequiredError(
            "The latest photo reconstruction does not match this furniture type"
        )

    try:
        latest_revision = session.scalar(
            select(func.max(FurniturePlan.revision)).where(
                FurniturePlan.furniture_id == source.furniture_id
            )
        )
        plan = FurniturePlan(
            furniture_id=source.furniture_id,
            revision=1 if latest_revision is None else latest_revision + 1,
            status=PlanStatus.DRAFT,
            furniture_type=source.furniture_type,
            source_reconstruction_id=reconstruction.id,
        )
        session.add(plan)
        session.flush()
        _add_reconstruction_components(session, plan, reconstruction)
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
        raise RuntimeError("Reconstructed revision could not be reloaded")
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
    component = FurnitureComponent(plan_id=plan.id, **payload.model_dump(mode="json"))
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
    merged = {
        field: getattr(component, field)
        for field in ComponentCreate.model_fields
    }
    merged.update(payload.model_dump(exclude_unset=True))
    try:
        validated = ComponentCreate.model_validate(merged).model_dump(mode="json")
    except ValidationError as exc:
        message = str(exc.errors()[0].get("msg", "Component geometry is invalid"))
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        raise ComponentGeometryValidationError(message) from exc
    for field in payload.model_fields_set:
        setattr(component, field, validated[field])
    if "rotation" in payload.model_fields_set and "rotation_y" not in payload.model_fields_set:
        component.rotation_y = validated["rotation"]
    if "rotation_y" in payload.model_fields_set and "rotation" not in payload.model_fields_set:
        component.rotation = validated["rotation_y"]
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
