"""Classifier boundary and classification workflow orchestration."""

import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.enums import FurnitureImageView, FurnitureType
from app.models.furniture import Furniture
from app.models.furniture_classification import FurnitureClassification
from app.services import furniture_images as image_service
from app.services.classification_state import get_classification
from app.services._persistence import commit_and_refresh
from app.services.image_storage import ImageStorage, ImageStorageNotFoundError

REQUIRED_VIEWS = tuple(FurnitureImageView)


class ClassifierUnavailableError(RuntimeError):
    """Raised when no classifier adapter is configured."""


class ClassificationPrerequisiteError(RuntimeError):
    """Raised when the five-view source set is incomplete or unavailable."""


class InvalidClassifierOutputError(RuntimeError):
    """Raised when an adapter returns a result outside its contract."""


@dataclass(frozen=True, slots=True)
class ClassificationImage:
    view: FurnitureImageView
    content_type: str
    checksum_sha256: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ClassificationPrediction:
    furniture_type: FurnitureType
    classifier_name: str
    confidence: Decimal | None = None
    classifier_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.furniture_type, FurnitureType):
            raise InvalidClassifierOutputError("Classifier returned an unsupported type")

        classifier_name = self.classifier_name.strip()
        if not classifier_name or len(classifier_name) > 100:
            raise InvalidClassifierOutputError("Classifier name must be 1 to 100 characters")
        object.__setattr__(self, "classifier_name", classifier_name)

        if self.classifier_version is not None:
            classifier_version = self.classifier_version.strip()
            if not classifier_version or len(classifier_version) > 100:
                raise InvalidClassifierOutputError(
                    "Classifier version must be 1 to 100 characters when provided"
                )
            object.__setattr__(self, "classifier_version", classifier_version)

        if self.confidence is not None:
            try:
                confidence = Decimal(str(self.confidence))
            except (InvalidOperation, ValueError) as exc:
                raise InvalidClassifierOutputError(
                    "Classifier confidence must be a decimal between 0 and 1"
                ) from exc
            if (
                not confidence.is_finite()
                or not Decimal("0") <= confidence <= Decimal("1")
            ):
                raise InvalidClassifierOutputError(
                    "Classifier confidence must be between 0 and 1"
                )
            object.__setattr__(self, "confidence", confidence)


class FurnitureClassifier(Protocol):
    """Replaceable adapter contract for a future real AI model."""

    def classify(
        self,
        images: tuple[ClassificationImage, ...],
    ) -> ClassificationPrediction: ...


class UnconfiguredFurnitureClassifier:
    """Honest default that never fabricates a classification."""

    def classify(
        self,
        images: tuple[ClassificationImage, ...],
    ) -> ClassificationPrediction:
        raise ClassifierUnavailableError("Furniture classifier is not configured")


def classify_furniture(
    session: Session,
    storage: ImageStorage,
    classifier: FurnitureClassifier,
    furniture: Furniture,
) -> FurnitureClassification:
    metadata = image_service.list_furniture_images(session, furniture.id)
    available_views = {image.view for image in metadata}
    missing_views = [view.value for view in REQUIRED_VIEWS if view not in available_views]
    if missing_views:
        missing = ", ".join(missing_views)
        raise ClassificationPrerequisiteError(
            f"Classification requires all five image views; missing: {missing}"
        )

    inputs: list[ClassificationImage] = []
    for image in metadata:
        try:
            data = storage.read(image.storage_key)
        except ImageStorageNotFoundError as exc:
            raise ClassificationPrerequisiteError(
                f"Stored content is unavailable for the {image.view.value} view"
            ) from exc
        if hashlib.sha256(data).hexdigest() != image.checksum_sha256:
            raise ClassificationPrerequisiteError(
                f"Stored content failed integrity validation for the {image.view.value} view"
            )
        inputs.append(
            ClassificationImage(
                view=image.view,
                content_type=image.content_type,
                checksum_sha256=image.checksum_sha256,
                data=data,
            )
        )

    prediction = classifier.classify(tuple(inputs))
    if not isinstance(prediction, ClassificationPrediction):
        raise InvalidClassifierOutputError(
            "Classifier adapter returned an invalid prediction object"
        )

    signature_source = "|".join(
        f"{image.view.value}:{image.checksum_sha256}" for image in inputs
    )
    input_signature = hashlib.sha256(signature_source.encode("ascii")).hexdigest()

    classification = get_classification(session, furniture.id)
    if classification is None:
        classification = FurnitureClassification(furniture_id=furniture.id)
        session.add(classification)
    classification.predicted_type = prediction.furniture_type
    classification.confidence = prediction.confidence
    classification.classifier_name = prediction.classifier_name
    classification.classifier_version = prediction.classifier_version
    classification.input_signature = input_signature
    furniture.furniture_type = prediction.furniture_type
    commit_and_refresh(session, classification)
    return classification
