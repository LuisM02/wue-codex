"""Health endpoint response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ServiceHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str


class DatabaseHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    database: Literal["reachable"]
