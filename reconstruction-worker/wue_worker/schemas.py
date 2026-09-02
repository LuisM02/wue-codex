"""Strict HTTP response schemas shared by the local worker endpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FurnitureType = Literal["chair", "dining_table", "bookshelf"]
FurnitureView = Literal["front", "back", "left", "right", "top"]


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    furniture_type: FurnitureType
    classifier_name: str
    classifier_version: str
    confidence: float = Field(ge=0, le=1)


class ProfilePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    u: float = Field(ge=0)
    v: float = Field(ge=0)


class PartProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str = Field(min_length=1, max_length=200)
    component_type: Literal["panel", "leg"]
    geometry_kind: Literal["box", "extruded_profile"]
    profile_points: list[ProfilePoint] | None = None
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    depth: float = Field(gt=0)
    x: float = 0
    y: float = 0
    z: float = 0
    rotation_x: float = 0
    rotation_y: float = 0
    rotation_z: float = 0
    quantity: int = Field(default=1, gt=0)
    sort_order: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    source_views: list[FurnitureView] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_profile(self) -> "PartProposal":
        if self.geometry_kind == "extruded_profile":
            if self.profile_points is None or len(self.profile_points) < 3:
                raise ValueError("Traced parts require at least three profile points")
            if any(point.u > self.width or point.v > self.height for point in self.profile_points):
                raise ValueError("Profile points must fit inside the part bounds")
        elif self.profile_points is not None:
            raise ValueError("Box parts cannot contain a traced profile")
        return self


class ReconstructionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name: str
    provider_version: str
    confidence: float = Field(ge=0, le=1)
    warnings: list[str]
    parts: list[PartProposal] = Field(min_length=1)


class WorkerHealth(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "WUE local vision worker"
    version: str


class ModelStatus(BaseModel):
    ready: bool
    pipeline: str
    uses_gpu: bool
    loaded_checkpoints: list[str]
    limitations: list[str]
