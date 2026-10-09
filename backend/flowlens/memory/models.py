"""Private acceptance ledger, preserving event, availability and recording clocks."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from flowlens.association import Link
from flowlens.contracts.models import Timed
from flowlens.intent.models import Candidate, Provenance

NAMESPACE = "analysis.intent.memory"
REDUCER = "memory-1"


class AcceptedEvent(Timed):
    id: UUID
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    reducer_version: Literal["memory-1"] = "memory-1"
    association_version: Literal["association-1-delay120000"] = "association-1-delay120000"
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    provenance: Provenance
    candidate: Candidate
    link: Link | None
    coverage_known: bool
    dependency_hashes: tuple[str, ...]
    invalidates: tuple[UUID, ...] = ()


class Invalidation(Timed):
    id: UUID
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    reducer_version: Literal["memory-1"] = "memory-1"
    targets: tuple[UUID, ...] = Field(min_length=1, max_length=4096)
    reason: Literal["CORRECTION", "REANALYSIS"]
