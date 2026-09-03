"""HTTP adapter for an isolated local GPU reconstruction worker."""

import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.enums import FurnitureType
from app.schemas.photo_reconstruction import ReconstructionPartProposal
from app.services.dimensions import CanonicalDimensions
from app.services.photo_reconstruction import (
    InvalidReconstructionOutputError,
    ReconstructionImage,
    ReconstructionPrediction,
    ReconstructionProviderUnavailableError,
)


class WorkerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(min_length=1, max_length=100)
    provider_version: str | None = Field(default=None, min_length=1, max_length=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    parts: list[ReconstructionPartProposal] = Field(min_length=1)


def _worker_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict) or not isinstance(
        payload.get("detail"), str
    ):
        return ""
    return payload["detail"].strip()[:300]


class HttpFurnitureReconstructor:
    """Send the five source images to a separately managed AI process."""

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

    def reconstruct(
        self,
        images: tuple[ReconstructionImage, ...],
        furniture_type: FurnitureType,
        dimensions: CanonicalDimensions,
    ) -> ReconstructionPrediction:
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            (
                image.view.value,
                (f"{image.view.value}", image.data, image.content_type),
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
        data = {
            "furniture_type": furniture_type.value,
            "width_mm": str(dimensions.width_mm),
            "height_mm": str(dimensions.height_mm),
            "depth_mm": str(dimensions.depth_mm),
            "image_manifest": json.dumps(manifest, separators=(",", ":")),
        }
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/v1/reconstruct",
                    data=data,
                    files=files,
                )
        except httpx.RequestError as exc:
            raise ReconstructionProviderUnavailableError(
                "The local photo reconstruction service is unavailable"
            ) from exc
        if response.status_code >= 500:
            raise ReconstructionProviderUnavailableError(
                _worker_error_detail(response)
                or (
                    "The local photo reconstruction service could not "
                    "complete the analysis"
                )
            )
        if response.status_code >= 400:
            raise InvalidReconstructionOutputError(
                _worker_error_detail(response)
                or "The local photo reconstruction service rejected the image set"
            )
        try:
            payload = WorkerResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise InvalidReconstructionOutputError(
                "The local photo reconstruction service returned invalid geometry"
            ) from exc
        return ReconstructionPrediction(
            parts=tuple(payload.parts),
            provider_name=payload.provider_name,
            provider_version=payload.provider_version,
            confidence=payload.confidence,
            warnings=tuple(payload.warnings),
        )
