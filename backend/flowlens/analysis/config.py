"""Local foundation configuration, deliberately not a provider readiness assertion."""

import hashlib
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from flowlens.contracts.models import Contract


class AnalysisConfig(Contract):
    profile: Literal["development", "test", "production"] = "development"
    config_version: Literal["b01-1"] = "b01-1"
    pipeline_enabled: Literal[False] = False

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ConfigurationRecord(Contract):
    """Immutable run binding; not a new frozen public wire contract."""

    id: UUID
    session_id: UUID
    analysis_run_id: UUID
    revision: int = Field(gt=0)
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    config: AnalysisConfig
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def valid_digest(self) -> Self:
        if self.config_hash != self.config.digest():
            raise ValueError("Configuration digest mismatch.")
        return self
