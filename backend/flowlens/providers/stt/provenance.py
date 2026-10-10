"""Private artifact codec and SDK reconstruction. No accepted-state or DB imports."""

import base64
import hashlib
from uuid import uuid5

from flowlens.analysis.transcript_records import RawTranscript
from flowlens.contracts.models import ArtifactSubmission
from flowlens.providers.stt.adapter import map_response, validate_binding
from flowlens.providers.stt.models import AuthorizedChunk, STTConfig, STTFailure
from google.cloud.speech_v2 import types

MAX_PROVENANCE_BYTES = 8 * 1024 * 1024
TRANSFORM = "stt-private-provenance-1"


def encode(raw: RawTranscript) -> bytes:
    payload = raw.model_dump_json().encode()
    if len(payload) > MAX_PROVENANCE_BYTES:
        raise STTFailure("STT_OUTPUT_LIMIT")
    return payload


def manifest(binding: AuthorizedChunk, payload: bytes) -> ArtifactSubmission:
    return ArtifactSubmission(
        id=uuid5(binding.lease.attempt_id, f"stt-provenance:{binding.chunk_id}"),
        session_id=binding.context.session_id,
        analysis_run_id=binding.lease.analysis_run_id,
        revision=binding.context.input_revision,
        kind="JSON_REPORT",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        source_asset_id=binding.chunk_id,
        transform_version=TRANSFORM,
        source_range=None,
        derivative_range=None,
        expires_at=None,
        required_capability="audio",
    )


def validate_raw(
    config: STTConfig, binding: AuthorizedChunk, audio: bytes, raw: RawTranscript
) -> None:
    """Rebuild every derived field from original protobuf and authoritative B02 input.

    Caller must resolve active lease/input/rights/config from authority, never from raw.
    Self-consistency is not cryptographic proof of a Google-origin response.
    """
    try:
        validate_binding(config, binding, audio)
        response = base64.b64decode(raw.response_base64, validate=True)
        if len(response) > config.max_response_bytes:
            raise STTFailure("STT_OUTPUT_LIMIT")
        reconstructed = map_response(config, binding, types.RecognizeResponse.deserialize(response))
        if reconstructed != raw:
            raise STTFailure("STT_OUTPUT_INVALID")
    except STTFailure:
        raise
    except Exception:
        raise STTFailure("STT_OUTPUT_INVALID") from None


def decode(
    config: STTConfig,
    binding: AuthorizedChunk,
    audio: bytes,
    artifact: ArtifactSubmission,
    payload: bytes,
) -> RawTranscript:
    if type(payload) is not bytes or len(payload) > MAX_PROVENANCE_BYTES:
        raise STTFailure("STT_OUTPUT_LIMIT")
    try:
        if artifact != manifest(binding, payload):
            raise STTFailure("STT_OUTPUT_INVALID")
        raw = RawTranscript.model_validate_json(payload)
        # Require our canonical bytes; reject alternate JSON/duplicate keys as well.
        if encode(raw) != payload:
            raise STTFailure("STT_OUTPUT_INVALID")
        validate_raw(config, binding, audio, raw)
        return raw
    except STTFailure:
        raise
    except Exception:
        raise STTFailure("STT_OUTPUT_INVALID") from None
