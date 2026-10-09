"""Six frozen read-only lookups, with server-owned context and output validation."""

import asyncio
from typing import cast

from flowlens.contracts.models import (
    Contract,
    Evidence,
    MemoryEvent,
    RequestContext,
    SourceEvent,
    Timed,
    ToolRequest,
    Track,
    TranscriptSegment,
)
from flowlens.contracts.ports import ContextReader, EvidenceService
from flowlens.core.errors import ContractError
from flowlens.intent.validation import visible
from flowlens.providers.gemini.models import GeminiConfig, GeminiFailure
from pydantic import ValidationError

TYPES: dict[str, type[Contract]] = {
    "get_entity_memory": MemoryEvent,
    "get_transcript_window": TranscriptSegment,
    "get_session_events": SourceEvent,
    "get_observed_tracks": Track,
    "get_active_rule_context": Evidence,
    "get_evidence": Evidence,
}


class BoundedTools:
    def __init__(
        self,
        config: GeminiConfig,
        context: RequestContext,
        reader: ContextReader,
        evidence: EvidenceService,
    ) -> None:
        self.config = config
        self.context = RequestContext.model_validate_json(context.model_dump_json())
        self.reader, self.evidence = reader, evidence
        self.calls = 0
        self.byte_count = 0

    async def lookup(self, request: ToolRequest) -> tuple[Contract, ...]:
        try:
            async with asyncio.timeout(self.config.tool_seconds):
                return await self._lookup(request)
        except TimeoutError:
            raise GeminiFailure("TOOL_TIMEOUT") from None

    async def _lookup(self, request: ToolRequest) -> tuple[Contract, ...]:
        try:
            request = ToolRequest.model_validate_json(request.model_dump_json())
        except ValidationError:
            raise GeminiFailure("TOOL_ARGUMENTS") from None
        context = self.context
        context.require("read", context.session_id, context.analysis_run_id)
        if "truth" in context.capabilities:
            # AI context must be a reduced observer context, never evaluator authority.
            raise GeminiFailure("TOOL_SCOPE")
        if request.window is not None and request.window.end_ms > context.as_of_ms:
            raise GeminiFailure("TOOL_SCOPE")
        if request.name in ("get_entity_memory", "get_observed_tracks"):
            if request.entity_id is None or request.evidence_id is not None:
                raise GeminiFailure("TOOL_ARGUMENTS")
        elif request.entity_id is not None:
            raise GeminiFailure("TOOL_ARGUMENTS")
        if request.name == "get_evidence":
            if request.evidence_id is None or request.window is not None:
                raise GeminiFailure("TOOL_ARGUMENTS")
        elif request.evidence_id is not None:
            raise GeminiFailure("TOOL_ARGUMENTS")
        if self.calls >= self.config.max_tools:
            raise GeminiFailure("TOOL_LIMIT")
        self.calls += 1
        try:
            # Sync frozen ports must implement their own IO timeout. Cancellation of
            # this await cannot kill an uncooperative thread; no writes are exposed.
            rows = await asyncio.wait_for(
                asyncio.to_thread(self.reader.lookup, context, request), self.config.tool_seconds
            )
        except TimeoutError:
            raise GeminiFailure("TOOL_TIMEOUT") from None
        except Exception:
            raise GeminiFailure("TOOL_UNAVAILABLE") from None
        if len(rows) > request.limit:
            raise GeminiFailure("TOOL_LIMIT")
        output = []
        for raw in rows:
            if not isinstance(raw, TYPES[request.name]):
                raise GeminiFailure("TOOL_OUTPUT")
            try:
                row = type(raw).model_validate_json(raw.model_dump_json())
            except ValidationError:
                raise GeminiFailure("TOOL_OUTPUT") from None
            try:
                if isinstance(row, Timed):
                    visible(context, row)
                    if request.window and not (
                        request.window.start_ms <= row.event_time_ms < request.window.end_ms
                    ):
                        raise ContractError("ACCESS_DENIED")
                    if isinstance(row, TranscriptSegment) and row.end_ms > context.as_of_ms:
                        raise ContractError("ACCESS_DENIED")
                    if request.entity_id is not None and (
                        cast(MemoryEvent | Track, row).entity_id != request.entity_id
                    ):
                        raise ContractError("ACCESS_DENIED")
                    if isinstance(row, (TranscriptSegment, MemoryEvent)):
                        for item in row.evidence:
                            if (
                                await asyncio.to_thread(self.evidence.resolve, context, item)
                                != item
                            ):
                                raise ContractError("EVIDENCE_UNAVAILABLE")
                elif isinstance(row, Evidence):
                    if (
                        (row.session_id, row.analysis_run_id, row.revision)
                        != (context.session_id, context.analysis_run_id, context.input_revision)
                        or row.end_ms is None
                        or row.end_ms > context.as_of_ms
                        or (request.evidence_id is not None and row.id != request.evidence_id)
                        or (request.name == "get_active_rule_context" and row.kind != "POLICY")
                        or await asyncio.to_thread(self.evidence.resolve, context, row) != row
                    ):
                        raise ContractError("ACCESS_DENIED")
            except ContractError:
                raise GeminiFailure("TOOL_SCOPE_OR_EVIDENCE") from None
            self.byte_count += len(row.model_dump_json().encode())
            if self.byte_count > self.config.max_tool_bytes:
                raise GeminiFailure("TOOL_LIMIT")
            output.append(row)
        return tuple(output)
