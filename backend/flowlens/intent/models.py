"""Versioned private records; frozen wire contracts remain unchanged."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from flowlens.contracts.models import Action, Contract, Evidence, Quality, SpeechAct, ToolRequest


class QuoteSlot(Contract):
    value: str | None = Field(max_length=256)
    quality: Quality
    evidence_ids: tuple[UUID, ...] = Field(max_length=16)
    alternatives: tuple[str, ...] = Field(max_length=16)
    unknowns: tuple[str, ...] = Field(max_length=16)


class Candidate(Contract):
    candidate_version: Literal["intent-1"] = "intent-1"
    id: UUID
    segment_id: UUID
    speech_act: SpeechAct
    role: Literal["CONTROLLER", "PILOT", "VEHICLE", "UNKNOWN"]
    entity_candidates: tuple[UUID, ...] = Field(max_length=16)
    callsign: QuoteSlot
    runway: QuoteSlot
    actions: tuple[Action, ...] = Field(max_length=8)
    action_evidence_ids: tuple[UUID, ...] = Field(max_length=16)
    condition: QuoteSlot
    negation: QuoteSlot
    evidence: tuple[Evidence, ...] = Field(min_length=1, max_length=32, repr=False)
    unknowns: tuple[str, ...] = Field(max_length=16)


class Response(Contract):
    """Structured lookup proposals and extraction are separate requests."""

    status: Literal["COMPLETE", "PARTIAL", "REFUSED"]
    tools: tuple[ToolRequest, ...] = Field(max_length=8)
    candidates: tuple[Candidate, ...] = Field(max_length=64)


class Provenance(Contract):
    profile: Literal["MOCK", "GOOGLE"]
    model: str
    api_version: str
    sdk_version: str
    prompt_version: str
    schema_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_hashes: tuple[str, ...]
    response_hashes: tuple[str, ...]
    calls: int = Field(ge=0, le=16)
    total_tokens: int | None = Field(ge=0)
