"""Bounded provider policy and safe diagnostics, outside frozen wire schemas."""

import hashlib
from typing import Literal

from flowlens.contracts.models import Contract
from flowlens.intent.models import Provenance, Response
from pydantic import Field


class GeminiConfig(Contract):
    config_version: Literal["gemini-1"] = "gemini-1"
    profile: Literal["MOCK", "GOOGLE"] = "MOCK"
    model: Literal["gemini-3.8-flash"] = "gemini-3.8-flash"
    api_version: Literal["v1beta"] = "v1beta"
    sdk_version: Literal["2.29.0"] = "2.29.0"
    prompt_version: Literal["intent-policy-1"] = "intent-policy-1"
    timeout_seconds: float = Field(default=30.0, gt=0, le=60)
    total_seconds: float = Field(default=120.0, gt=0, le=300)
    retries: int = Field(default=2, ge=0, le=2)
    concurrency: int = Field(default=2, ge=1, le=4)
    max_calls: int = Field(default=8, ge=1, le=16)
    max_input_bytes: int = Field(default=65536, ge=1024, le=262144)
    max_output_bytes: int = Field(default=65536, ge=1024, le=262144)
    max_output_tokens: int = Field(default=8192, ge=256, le=16384)
    max_total_tokens: int = Field(default=65536, ge=256, le=262144)
    max_tool_rounds: int = Field(default=4, ge=0, le=4)
    max_tools: int = Field(default=8, ge=0, le=8)
    max_tool_bytes: int = Field(default=65536, ge=256, le=131072)
    tool_seconds: float = Field(default=5.0, gt=0, le=10)

    def digest(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class Reply(Contract):
    text: str = Field(repr=False)
    status: Literal["COMPLETE", "PARTIAL", "REFUSED"]
    input_tokens: int | None = Field(ge=0)
    output_tokens: int | None = Field(ge=0)
    total_tokens: int | None = Field(ge=0)


class Extraction(Contract):
    response: Response
    provenance: Provenance


class GeminiFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
