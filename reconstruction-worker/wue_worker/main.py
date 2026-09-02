"""FastAPI entry point for the isolated local furniture vision worker."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from . import __version__
from .geometry import classify as classify_views
from .geometry import reconstruct as reconstruct_views
from .imaging import ImageSetRejected, REQUIRED_VIEWS, analyze_image, validate_view_set
from .schemas import (
    ClassificationResponse,
    ModelStatus,
    ReconstructionResponse,
    WorkerHealth,
)

app = FastAPI(title="WUE local vision worker", version=__version__)


async def _read_views(
    files: dict[str, UploadFile], manifest_json: str
) -> dict:
    try:
        manifest_items = json.loads(manifest_json)
        manifest = {
            item["view"]: item["checksum_sha256"] for item in manifest_items
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail="Invalid image checksum manifest"
        ) from exc
    if set(manifest) != set(REQUIRED_VIEWS):
        raise HTTPException(
            status_code=422,
            detail="The manifest must contain exactly five named views",
        )
    analyzed = {}
    try:
        for name in REQUIRED_VIEWS:
            data = await files[name].read()
            if hashlib.sha256(data).hexdigest() != manifest[name]:
                raise ImageSetRejected(
                    f"The {name} image checksum does not match its manifest"
                )
            analyzed[name] = analyze_image(name, data)
    except ImageSetRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return analyzed


@app.get("/health", response_model=WorkerHealth)
def health() -> WorkerHealth:
    return WorkerHealth(version=__version__)


@app.get("/v1/model-status", response_model=ModelStatus)
def model_status() -> ModelStatus:
    return ModelStatus(
        ready=True,
        pipeline="five-view-silhouette-baseline",
        uses_gpu=False,
        loaded_checkpoints=[],
        limitations=[
            "Best with one furniture item against a plain contrasting background",
            "Semantic parts are inferred from traced silhouettes",
            "SAM 2 and dense multi-view depth are not loaded in this baseline",
        ],
    )


@app.post("/v1/classify", response_model=ClassificationResponse)
async def classify(
    image_manifest: Annotated[str, Form()],
    front: Annotated[UploadFile, File()],
    back: Annotated[UploadFile, File()],
    left: Annotated[UploadFile, File()],
    right: Annotated[UploadFile, File()],
    top: Annotated[UploadFile, File()],
) -> ClassificationResponse:
    views = await _read_views(
        {
            "front": front,
            "back": back,
            "left": left,
            "right": right,
            "top": top,
        },
        image_manifest,
    )
    try:
        validate_view_set(views)
        furniture_type, confidence = classify_views(views)
    except (ImageSetRejected, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ClassificationResponse(
        furniture_type=furniture_type,
        classifier_name="wue-image-structure",
        classifier_version=__version__,
        confidence=confidence,
    )


@app.post("/v1/reconstruct", response_model=ReconstructionResponse)
async def reconstruct(
    furniture_type: Annotated[
        str, Form(pattern="^(chair|dining_table|bookshelf)$")
    ],
    width_mm: Annotated[float, Form(gt=0)],
    height_mm: Annotated[float, Form(gt=0)],
    depth_mm: Annotated[float, Form(gt=0)],
    image_manifest: Annotated[str, Form()],
    front: Annotated[UploadFile, File()],
    back: Annotated[UploadFile, File()],
    left: Annotated[UploadFile, File()],
    right: Annotated[UploadFile, File()],
    top: Annotated[UploadFile, File()],
) -> ReconstructionResponse:
    views = await _read_views(
        {
            "front": front,
            "back": back,
            "left": left,
            "right": right,
            "top": top,
        },
        image_manifest,
    )
    try:
        warnings = validate_view_set(
            views, (width_mm, height_mm, depth_mm)
        )
        return reconstruct_views(
            furniture_type,
            views,
            width_mm,
            height_mm,
            depth_mm,
            warnings,
        )
    except (ImageSetRejected, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
