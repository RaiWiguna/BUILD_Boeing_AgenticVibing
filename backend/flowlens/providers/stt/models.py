"""Authorized private B02 chunk binding and explicit provider configuration."""

import hashlib
from typing import Literal, Self
from uuid import UUID

from flowlens.audio.models import AudioRecord, PreparationMetadata
from flowlens.contracts.models import JobLease, RequestContext
from pydantic import Field, model_validator


class STTConfig(AudioRecord):
    config_version: Literal["stt-v2-1"] = "stt-v2-1"
    project: str = Field(pattern=r"^[a-z][a-z0-9-]{4,61}[a-z0-9]$")
    region: str = Field(pattern=r"^(global|us|eu|[a-z]+-[a-z]+[0-9])$")
    endpoint: str = Field(max_length=128)
    recognizer: str = Field(max_length=256)
    model: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    language: str = Field(pattern=r"^[a-z]{2,3}-[A-Z]{2}$")
    word_confidence: bool = False
    timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    max_concurrency: int = Field(default=2, ge=1, le=2)
    max_attempts: int = Field(default=1, ge=1, le=3)
    retry_delay_seconds: float = Field(default=0.25, ge=0, le=5)
    max_calls: int = Field(default=512, ge=1, le=4096)
    max_response_bytes: int = Field(default=1048576, ge=1, le=1048576)
    max_words: int = Field(default=8192, ge=1, le=8192)
    max_hypotheses: int = Field(default=256, ge=1, le=256)
    max_text_characters: int = Field(default=65536, ge=1, le=65536)

    @model_validator(mode="after")
    def routing(self) -> Self:
        expected = (
            "speech.googleapis.com"
            if self.region == "global"
            else (f"{self.region}-speech.googleapis.com")
        )
        prefix = f"projects/{self.project}/locations/{self.region}/recognizers/"
        if self.endpoint != expected or not self.recognizer.startswith(prefix):
            raise ValueError("Provider routing mismatch.")
        name = self.recognizer.removeprefix(prefix)
        if (
            not name
            or len(name) > 63
            or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in name)
        ):
            raise ValueError("Invalid recognizer.")
        return self

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ProviderApproval(AudioRecord):
    """Operator/platform attestation, never model-supplied readiness or budget policy."""

    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    compatibility: Literal["VERIFIED", "UNVERIFIED"]
    api_enabled: bool
    identity_authorized: bool
    billing_authorized: bool
    data_logging: Literal["DISABLED", "ENABLED", "UNKNOWN"]


class AuthorizedChunk(AudioRecord):
    context: RequestContext
    lease: JobLease
    chunk_id: UUID
    preparation: PreparationMetadata = Field(repr=False)
    chunk_index: int = Field(ge=0)
    cloud_permission: Literal["ALLOWED", "DENIED", "UNDETERMINED"]
    local_permission: Literal["ALLOWED", "DENIED", "UNDETERMINED"]
    approval: ProviderApproval


class STTFailure(Exception):
    """Only allowlisted codes escape. Never retain a provider exception/message."""

    def __init__(self, code: str) -> None:
        if code not in {
            "STT_OUTPUT_INVALID",
            "STT_OUTPUT_LIMIT",
            "STT_PERMISSION_DENIED",
            "STT_PROFILE_UNVERIFIED",
            "STT_BINDING_INVALID",
            "STT_AUDIO_INVALID",
            "STT_TIMEOUT",
            "STT_LOST_LEASE",
            "STT_DEADLINE",
            "STT_LEASE_EXPIRED",
            "STT_DUPLICATE_OR_LIMIT",
            "STT_CALL_LIMIT",
            "STT_QUOTA",
            "STT_UNAVAILABLE",
            "STT_PROVIDER_DENIED",
            "STT_INVALID_OR_UNAVAILABLE",
            "STT_CLIENT_CLOSE_FAILED",
            "STT_CANCELLED",
            "STT_SHUTDOWN",
            "STT_CONTROL_FAILED",
            "STT_BUDGET_EXCEEDED",
        }:
            code = "STT_CONTROL_FAILED"
        self.code = code
        super().__init__(code)
