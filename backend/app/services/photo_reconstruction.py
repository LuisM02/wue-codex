"""Photo-to-part AI boundary and reconstruction persistence workflow."""

import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.enums import FurnitureImageView, FurnitureType
from app.models.furniture import Furniture
from app.models.furniture_reconstruction import FurnitureReconstruction
from app.models.furniture_reconstruction_part import FurnitureReconstructionPart
from app.schemas.photo_reconstruction import ReconstructionPartProposal
from app.services import dimensions as dimension_service
from app.services import furniture_images as image_service
from app.services._persistence import commit
from app.services.image_storage import ImageStorage, ImageStorageNotFoundError
from app.services.reconstruction_state import get_reconstruction

REQUIRED_VIEWS = tuple(FurnitureImageView)


class ReconstructionProviderUnavailableError(RuntimeError):
    """Raised when no real photo reconstruction provider is configured."""


class ReconstructionPrerequisiteError(RuntimeError):
    """Raised when the exact five-view input set cannot be reconstructed."""


class ReconstructionInputRejectedError(RuntimeError):
    """Raised when the worker cannot use the supplied photo evidence."""


class InvalidReconstructionOutputError(RuntimeError):
    """Raised when a provider response violates the WUE geometry contract."""


@dataclass(frozen=True, slots=True)
class ReconstructionImage:
    view: FurnitureImageView
    content_type: str
    checksum_sha256: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ReconstructionPrediction:
    parts: tuple[ReconstructionPartProposal, ...]
    provider_name: str
    provider_version: str | None = None
    confidence: Decimal | None = None
    warnings: tuple[str, ...] = ()


class FurnitureReconstructor(Protocol):
    """Adapter implemented by a local or remote multi-view AI pipeline."""

    def reconstruct(
        self,
        images: tuple[ReconstructionImage, ...],
        furniture_type: FurnitureType,
        dimensions: dimension_service.CanonicalDimensions,
    ) -> ReconstructionPrediction: ...


class UnconfiguredFurnitureReconstructor:
    """Honest default: never replaces photographs with generic geometry."""

    def reconstruct(
        self,
        images: tuple[ReconstructionImage, ...],
        furniture_type: FurnitureType,
        dimensions: dimension_service.CanonicalDimensions,
    ) -> ReconstructionPrediction:
        raise ReconstructionProviderUnavailableError(
            "Photo reconstruction AI is not configured; WUE will not generate a generic substitute"
        )


def build_input_signature(images: tuple[ReconstructionImage, ...]) -> str:
    source = "|".join(
        f"{image.view.value}:{image.checksum_sha256}" for image in images
    )
    return hashlib.sha256(source.encode("ascii")).hexdigest()


def _validate_prediction(
    prediction: object,
) -> ReconstructionPrediction:
    if not isinstance(prediction, ReconstructionPrediction):
        raise InvalidReconstructionOutputError(
            "Reconstruction adapter returned an invalid prediction object"
        )
    name = prediction.provider_name.strip()
    if not name or len(name) > 100:
        raise InvalidReconstructionOutputError(
            "Reconstruction provider name must be 1 to 100 characters"
        )
    version = prediction.provider_version
    if version is not None and (not version.strip() or len(version.strip()) > 100):
        raise InvalidReconstructionOutputError(
            "Reconstruction provider version must be 1 to 100 characters"
        )
    if not prediction.parts:
        raise InvalidReconstructionOutputError(
            "Reconstruction provider returned no furniture parts"
        )
    names = [part.component_name.strip().casefold() for part in prediction.parts]
    if len(set(names)) != len(names):
        raise InvalidReconstructionOutputError(
            "Reconstruction part names must be unique"
        )
    orders = [part.sort_order for part in prediction.parts]
    if len(set(orders)) != len(orders):
        raise InvalidReconstructionOutputError(
            "Reconstruction part sort orders must be unique"
        )
    confidence = prediction.confidence
    if confidence is not None:
        try:
            confidence = Decimal(str(confidence))
        except (InvalidOperation, ValueError) as exc:
            raise InvalidReconstructionOutputError(
                "Reconstruction confidence must be between 0 and 1"
            ) from exc
        if not confidence.is_finite() or not Decimal("0") <= confidence <= Decimal("1"):
            raise InvalidReconstructionOutputError(
                "Reconstruction confidence must be between 0 and 1"
            )
    warnings = tuple(item.strip() for item in prediction.warnings)
    if any(not item or len(item) > 500 for item in warnings):
        raise InvalidReconstructionOutputError(
            "Reconstruction warnings must be 1 to 500 characters"
        )
    return ReconstructionPrediction(
        parts=prediction.parts,
        provider_name=name,
        provider_version=None if version is None else version.strip(),
        confidence=confidence,
        warnings=warnings,
    )


def reconstruct_furniture(
    session: Session,
    storage: ImageStorage,
    provider: FurnitureReconstructor,
    furniture: Furniture,
) -> FurnitureReconstruction:
    if furniture.furniture_type is None:
        raise ReconstructionPrerequisiteError(
            "Furniture recognition is required before part reconstruction"
        )
    dimensions_model = dimension_service.get_dimensions(session, furniture.id)
    if dimensions_model is None:
        raise ReconstructionPrerequisiteError(
            "Overall dimensions are required to scale photo-derived parts"
        )
    metadata = image_service.list_furniture_images(session, furniture.id)
    available = {image.view for image in metadata}
    missing = [view.value for view in REQUIRED_VIEWS if view not in available]
    if missing:
        raise ReconstructionPrerequisiteError(
            "Photo reconstruction requires all five image views; missing: "
            + ", ".join(missing)
        )

    images: list[ReconstructionImage] = []
    for image in metadata:
        try:
            data = storage.read(image.storage_key)
        except ImageStorageNotFoundError as exc:
            raise ReconstructionPrerequisiteError(
                f"Stored content is unavailable for the {image.view.value} view"
            ) from exc
        if hashlib.sha256(data).hexdigest() != image.checksum_sha256:
            raise ReconstructionPrerequisiteError(
                f"Stored content failed integrity validation for the {image.view.value} view"
            )
        images.append(
            ReconstructionImage(
                view=image.view,
                content_type=image.content_type,
                checksum_sha256=image.checksum_sha256,
                data=data,
            )
        )

    canonical = dimension_service.CanonicalDimensions(
        width_mm=dimensions_model.width_mm,
        height_mm=dimensions_model.height_mm,
        depth_mm=dimensions_model.depth_mm,
    )
    prediction = _validate_prediction(
        provider.reconstruct(tuple(images), furniture.furniture_type, canonical)
    )
    reconstruction = get_reconstruction(session, furniture.id)
    if reconstruction is None:
        reconstruction = FurnitureReconstruction(
            furniture_id=furniture.id,
            input_signature=build_input_signature(tuple(images)),
            furniture_type=furniture.furniture_type,
            provider_name=prediction.provider_name,
            provider_version=prediction.provider_version,
            confidence=prediction.confidence,
            warnings=list(prediction.warnings),
        )
        session.add(reconstruction)
    else:
        reconstruction.parts.clear()
        session.flush()
        reconstruction.input_signature = build_input_signature(tuple(images))
        reconstruction.furniture_type = furniture.furniture_type
        reconstruction.provider_name = prediction.provider_name
        reconstruction.provider_version = prediction.provider_version
        reconstruction.confidence = prediction.confidence
        reconstruction.warnings = list(prediction.warnings)
    for proposal in prediction.parts:
        payload = proposal.model_dump(mode="json")
        reconstruction.parts.append(
            FurnitureReconstructionPart(
                component_name=payload["component_name"],
                component_type=payload["component_type"],
                geometry_kind=payload["geometry_kind"],
                profile_points=payload["profile_points"],
                width=payload["width"],
                height=payload["height"],
                depth=payload["depth"],
                x=payload["x"],
                y=payload["y"],
                z=payload["z"],
                rotation_x=payload["rotation_x"],
                rotation_y=payload["rotation_y"],
                rotation_z=payload["rotation_z"],
                quantity=payload["quantity"],
                sort_order=payload["sort_order"],
                confidence=payload["confidence"],
                source_views=payload["source_views"],
            )
        )
    commit(session)
    stored = get_reconstruction(session, furniture.id)
    if stored is None:  # pragma: no cover - persistence invariant
        raise RuntimeError("Created reconstruction could not be reloaded")
    return stored
