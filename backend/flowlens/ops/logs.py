"""Structured allowlist events: no exception text, request bodies, headers or queries."""

import logging
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, ValidationError

from flowlens.clocks.normalization import MetadataModel

Stage = Literal[
    "AUDIO", "STT", "INTENT", "ASSOCIATION", "MEMORY", "FINDINGS", "BRIEF", "QUERY", "EXPORT"
]


class Event(MetadataModel):
    event: Literal["HTTP_REQUEST", "JOB_ATTEMPT_FINISHED"]
    request_id: UUID | None = None
    session_id: UUID | None = None
    run_id: UUID | None = None
    job_id: UUID | None = None
    attempt_id: UUID | None = None
    stage: Stage | None = None
    status: Annotated[int, Field(ge=100, le=599)] | None = None
    latency_ms: Annotated[int, Field(ge=0)] | None = None
    charged_microunits: Annotated[int, Field(ge=0)] | None = None
    config_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    input_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    measurement: Literal["UNTIL_HEADERS", "COMMITTED_ATTEMPT"] | None = None


def emit(**fields: object) -> None:
    try:
        item = Event.model_validate(fields)
    except ValidationError:
        return
    try:
        logging.getLogger("flowlens.ops").info(item.model_dump_json(exclude_none=True))
    except Exception:
        # Telemetry delivery cannot invalidate an accepted DB commit or expose handler errors.
        return


def configure() -> None:
    """Supported launcher emits JSON INFO on the dedicated A logger, without SDK verbosity."""
    logger = logging.getLogger("flowlens.ops")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.name = "flowlens-json"
    for old in list(logger.handlers):
        if old.name == "flowlens-json":
            logger.removeHandler(old)
            old.close()
    logger.addHandler(handler)
