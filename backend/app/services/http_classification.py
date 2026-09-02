"""HTTP adapter for classification performed by the local vision worker."""

import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.enums import FurnitureType
from app.services.classification import (
    ClassificationImage,
    ClassificationPrediction,
    ClassifierUnavailableError,
    InvalidClassifierOutputError,
)


class WorkerClassificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    furniture_type: FurnitureType
    classifier_name: str = Field(min_length=1, max_length=100)
    classifier_version: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    confidence: float | None = Field(default=None, ge=0, le=1)


class HttpFurnitureClassifier:
    """Send all source photographs to the separately managed vision process."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def classify(
        self, images: tuple[ClassificationImage, ...]
    ) -> ClassificationPrediction:
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            (
                image.view.value,
                (image.view.value, image.data, image.content_type),
            )
            for image in images
        ]
        manifest: list[dict[str, Any]] = [
            {
                "view": image.view.value,
                "checksum_sha256": image.checksum_sha256,
            }
            for image in images
        ]
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/v1/classify",
                    data={
                        "image_manifest": json.dumps(
                            manifest, separators=(",", ":")
                        )
                    },
                    files=files,
                )
        except httpx.RequestError as exc:
            raise ClassifierUnavailableError(
                "The local furniture recognition service is unavailable"
            ) from exc
        if response.status_code >= 500:
            raise ClassifierUnavailableError(
                "The local furniture recognition service could not complete the analysis"
            )
        if response.status_code >= 400:
            try:
                detail = str(response.json().get("detail", "")).strip()
            except ValueError:
                detail = ""
            raise InvalidClassifierOutputError(
                detail
                or "The local furniture recognition service rejected the image set"
            )
        try:
            payload = WorkerClassificationResponse.model_validate(
                response.json()
            )
        except (ValueError, ValidationError) as exc:
            raise InvalidClassifierOutputError(
                "The local furniture recognition service returned an invalid result"
            ) from exc
        return ClassificationPrediction(
            furniture_type=payload.furniture_type,
            classifier_name=payload.classifier_name,
            classifier_version=payload.classifier_version,
            confidence=payload.confidence,
        )
