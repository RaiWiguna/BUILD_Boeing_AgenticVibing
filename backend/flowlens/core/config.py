"""Baseline settings; production composition remains unavailable until Phase 10."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Profile = Literal["test", "development", "production"]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    profile: Profile = "development"
    api_workers: Literal[1] = 1
    contract_version: Literal["1.0.0"] = "1.0.0"
    gemini_model: str = "gemini-3.8-flash"
    gemini_transport: Literal["GEMINI_DEVELOPER_INTERACTIONS"] = "GEMINI_DEVELOPER_INTERACTIONS"
    max_tool_rounds: int = Field(default=4, ge=1, le=4)
    max_tool_calls: int = Field(default=8, ge=1, le=8)
    provider_timeout_seconds: int = Field(default=60, ge=1, le=300)

    @model_validator(mode="after")
    def baseline_only(self) -> Self:
        if self.profile == "production":
            raise ValueError(
                "production requires real A/B composition and G-BE; baseline unavailable"
            )
        return self
