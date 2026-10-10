"""Explicit observed DTO projection; raw repositories and evaluator truth are separate inputs."""

from typing import Any, Literal

from flowlens.auth.permissions import Permissions
from flowlens.contracts.models import (
    PUBLIC_MODELS,
    AnalysisRun,
    Asset,
    Brief,
    Contract,
    Evidence,
    FactualItem,
    GeometryResult,
    Option,
    RequestContext,
    Scoped,
    Snapshot,
    SourceEvent,
    SourceManifest,
    SourceQualityChanged,
    StreamEvent,
    Timed,
    Usage,
)
from flowlens.core.errors import ContractError
from flowlens.storage.sqlite.database import UnitOfWork
from pydantic import ValidationError

NESTED_MODELS = (*PUBLIC_MODELS, Asset, FactualItem, Usage)
SOURCE_SCOPED = (SourceEvent, Evidence, GeometryResult, SourceQualityChanged)


def check_projection(value: Contract, context: RequestContext) -> None:
    """Check every nested scope, not just the outer response envelope."""
    if type(value) not in NESTED_MODELS:
        raise ContractError("ACCESS_DENIED")
    if isinstance(value, Scoped):
        if value.session_id != context.session_id or value.revision != context.input_revision:
            raise ContractError("ACCESS_DENIED")
        if value.analysis_run_id != context.analysis_run_id and not (
            isinstance(value, SOURCE_SCOPED) and value.analysis_run_id is None
        ):
            raise ContractError("ACCESS_DENIED")
    if isinstance(value, Timed) and (
        value.event_time_ms > context.as_of_ms
        or (
            context.mode == "AS_KNOWN"
            and (value.available_time_ms is None or value.available_time_ms > context.as_of_ms)
        )
    ):
        raise ContractError("ACCESS_DENIED")
    if isinstance(value, (Brief, Option)) and value.as_of_ms > context.as_of_ms:
        raise ContractError("ACCESS_DENIED")
    if isinstance(value, Snapshot) and (
        value.mode != context.mode or value.as_of_ms != context.as_of_ms
    ):
        raise ContractError("ACCESS_DENIED")
    if isinstance(value, StreamEvent) and (
        value.session_id != context.session_id or value.analysis_run_id != context.analysis_run_id
    ):
        raise ContractError("ACCESS_DENIED")
    if isinstance(value, AnalysisRun) and (
        context.analysis_run_id is not None and value.id != context.analysis_run_id
    ):
        raise ContractError("ACCESS_DENIED")
    for field in type(value).model_fields:
        child = getattr(value, field)
        if isinstance(child, Contract):
            check_projection(child, context)
        elif isinstance(child, list):
            for item in child:
                if isinstance(item, Contract):
                    check_projection(item, context)


def public_dto(
    permissions: Permissions,
    uow: UnitOfWork,
    context: RequestContext,
    value: object,
    *,
    classification: Literal["OBSERVED", "TRUTH", "PRIVATE"] = "OBSERVED",
) -> dict[str, Any]:
    """Project a server-selected observed DTO inside its live authorization UOW.

    Classification comes from trusted source/evaluator ownership, never a query/body field.
    Truth has no frozen public wire model and cannot be dumped through this boundary, even
    with a truth grant. A future evaluator route needs its own explicit reviewed contract.
    """
    permissions.enforce(uow, context)
    context.require("read", context.session_id)
    if (
        "worker" in context.capabilities
        or classification != "OBSERVED"
        or type(value) not in PUBLIC_MODELS
        or not isinstance(value, (Scoped, SourceManifest, StreamEvent))
    ):
        raise ContractError("ACCESS_DENIED")
    check_projection(value, context)
    try:
        # Re-run validators after model_copy/list mutations; never use serialize_as_any.
        dto = type(value).model_validate_json(value.model_dump_json())
    except (ValidationError, ValueError, TypeError):
        raise ContractError("ACCESS_DENIED") from None
    if isinstance(dto, SourceManifest):
        if dto.session_id != context.session_id or dto.revision != context.input_revision:
            raise ContractError("ACCESS_DENIED")
        current = permissions.require_source_rights(uow, context, dto.id)
        # Use current persisted rights/metadata, not a stale caller-supplied manifest.
        assets = (
            [permissions.authorize_asset(uow, context, asset.id) for asset in current.assets]
            if "audio" in context.capabilities
            else []
        )
        dto = current.model_copy(update={"assets": assets})
    return dto.model_dump(mode="json")
