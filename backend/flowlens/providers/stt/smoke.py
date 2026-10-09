"""Opt-in real synthetic smoke. Default performs no credential lookup or paid RPC.

Operator supplies a local approved profile and credentials; never pass secrets in
arguments or chat. No provisioning/API/logging/billing changes are performed here.
"""

import argparse
import asyncio
import json
import math
import sys
import time
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from flowlens.audio import AudioTools, prepare_audio
from flowlens.audio.models import AudioRecord
from flowlens.audio.preparation import digest
from flowlens.contracts.models import JobLease, RequestContext, SourceManifest
from flowlens.providers.stt.adapter import GoogleClient, STTExecutor, validate_authorization
from flowlens.providers.stt.models import AuthorizedChunk, ProviderApproval, STTConfig, STTFailure
from google.auth import load_credentials_from_file
from google.auth.credentials import Credentials
from pydantic import Field

FIXTURE_HASH = "cf3baa73bc59e37ddbd16e99e8a5f7493c22057d01c02b4030585b88486ba044"
MANIFEST_HASH = "37472d982c0591f32fe36897aebca727d56d5b812c82ce8f3a201cd7d24cf008"


class SmokeProfile(AudioRecord):
    config: STTConfig
    approval: ProviderApproval
    quota_verified: bool
    synthetic_cloud_rights_verified: bool
    budget_microunits: int = Field(gt=0)
    # Operator's conservative price incl. minimum charge/rounding, not guessed pricing.
    price_microunits_per_second: int = Field(gt=0)


def preflight(profile: SmokeProfile, credentials_present: bool) -> tuple[str, ...]:
    blockers = []
    config, approval = profile.config, profile.approval
    if (
        approval.config_hash != config.digest()
        or approval.compatibility != "VERIFIED"
        or not approval.api_enabled
        or not approval.identity_authorized
        or not approval.billing_authorized
        or approval.data_logging != "DISABLED"
    ):
        blockers.append("PROFILE_UNVERIFIED")
    if not credentials_present:
        blockers.append("CREDENTIALS_UNAVAILABLE")
    if not profile.quota_verified:
        blockers.append("QUOTA_UNVERIFIED")
    if not profile.synthetic_cloud_rights_verified:
        blockers.append("RIGHTS_UNVERIFIED")
    if config.max_attempts != 1 or config.max_calls != 1 or config.timeout_seconds > 30:
        blockers.append("SMOKE_LIMITS_INVALID")
    # Single fixture <9 seconds. Reserve conservatively to whole seconds before RPC.
    if profile.budget_microunits < 9 * profile.price_microunits_per_second:
        blockers.append("BUDGET_INSUFFICIENT")
    return tuple(blockers)


async def run_smoke(
    profile: SmokeProfile, credentials: Credentials, root: Path
) -> dict[str, object]:
    if preflight(profile, True):
        raise STTFailure("STT_PROFILE_UNVERIFIED")
    source = root / "tests/fixtures/audio/hold-short.wav"
    manifest_path = root / "tests/fixtures/manifests/synthetic-audio.json"
    if (
        digest(source, max_bytes=1_000_000) != FIXTURE_HASH
        or digest(manifest_path, max_bytes=65536) != MANIFEST_HASH
    ):
        raise STTFailure("STT_PERMISSION_DENIED")
    with manifest_path.open("rb") as stream:
        manifest = SourceManifest.model_validate_json(stream.read(65537))
    if manifest.source_kind != "SYNTHETIC" or not manifest.permissions.cloud:
        raise STTFailure("STT_PERMISSION_DENIED")
    with TemporaryDirectory(prefix="flowlens-stt-smoke-") as temporary:
        scratch = Path(temporary).resolve()
        with prepare_audio(
            source=source.resolve(),
            raw_root=source.parent.resolve(),
            scratch_root=scratch,
            source_id=manifest.id,
            asset=manifest.assets[0],
            clock=manifest.clock,
            tools=AudioTools.discover(),
        ) as prepared:
            if len(prepared.metadata.chunks) != 1:
                raise STTFailure("STT_BINDING_INVALID")
            chunk = prepared.metadata.chunks[0]
            audio = (prepared.directory / chunk.filename).read_bytes()
            config = profile.config
            now = time.time_ns() // 1_000_000
            context = RequestContext(
                actor_id=uuid4(),
                capabilities=["worker", "audio"],
                session_id=manifest.session_id,
                analysis_run_id=uuid4(),
                input_revision=1,
                input_hash=FIXTURE_HASH,
                as_of_ms=0,
                mode="DEBRIEF",
                request_id=uuid4(),
            )
            chunk_id = uuid4()
            lease = JobLease(
                session_id=context.session_id,
                analysis_run_id=context.analysis_run_id,
                revision=1,
                job_id=uuid4(),
                attempt_id=uuid4(),
                lease_id=uuid4(),
                owner_id=context.actor_id,
                stage="STT",
                input_hash=context.input_hash,
                config_hash=config.digest(),
                expires_ms=now + 60000,
                deadline_ms=now + 60000,
                budget_microunits=profile.budget_microunits,
                asset_ids=[chunk_id],
            )
            binding = AuthorizedChunk(
                context=context,
                lease=lease,
                chunk_id=chunk_id,
                preparation=prepared.metadata,
                chunk_index=0,
                cloud_permission="ALLOWED",
                local_permission="ALLOWED",
                approval=profile.approval,
            )
            validate_authorization(config, binding)
            reserved = 0

            def reserve(active: JobLease, audio_ms: int) -> None:
                nonlocal reserved
                cost = math.ceil(audio_ms / 1000) * profile.price_microunits_per_second
                if active != lease or reserved + cost > profile.budget_microunits:
                    raise STTFailure("STT_BUDGET_EXCEEDED")
                reserved += cost

            executor = STTExecutor(config, GoogleClient(config, credentials))
            try:
                raw, usage = await executor.transcribe(
                    binding, audio, lambda: lease, reserve=reserve
                )
                return {
                    "status": "EXECUTED",
                    "profile": "REAL_GOOGLE_STT",
                    "provider_calls": executor.calls,
                    "config_hash": config.digest(),
                    "response_hash": raw.response_hash,
                    "response_status": raw.status,
                    "latency_ms": usage.latency_ms,
                    "audio_ms": usage.audio_ms,
                    "attempted_audio_ms": executor.attempted_audio_ms,
                    "reserved_microunits": reserved,
                    "actual_cost_microunits": None,
                    "label_status": "NOT_GOLD/NOT_DOMAIN_VALIDATED",
                    "scratch": "disposable-cleaned",
                }
            except STTFailure as exc:
                return {
                    "status": "FAILED",
                    "profile": "REAL_GOOGLE_STT",
                    "code": exc.code,
                    "provider_calls": executor.calls,
                    "attempted_audio_ms": executor.attempted_audio_ms,
                    "reserved_microunits": reserved,
                    "actual_cost_microunits": None,
                    "config_hash": config.digest(),
                    "scratch": "disposable-cleaned",
                }
            finally:
                await executor.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--credentials", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    report: dict[str, object] = {
        "unit": "B03_REAL_SMOKE",
        "status": "BLOCKED",
        "provider_calls": 0,
        "sdk_version": version("google-cloud-speech"),
        "api_version": "v2",
        "python": sys.version.split()[0],
        "pipeline_ready": False,
    }
    try:
        if args.profile is None:
            report["blockers"] = ["APPROVED_PROFILE_UNAVAILABLE", "CREDENTIALS_UNAVAILABLE"]
        else:
            with args.profile.open("rb") as stream:
                payload = stream.read(65537)
            if len(payload) > 65536:
                raise ValueError("bounded profile")
            profile = SmokeProfile.model_validate_json(payload)
            present = args.credentials is not None and args.credentials.is_file()
            blockers = preflight(profile, present)
            report.update(config_hash=profile.config.digest(), blockers=blockers)
            if not blockers:
                if not args.execute:
                    report["status"] = "PREFLIGHT_ONLY"
                else:
                    # google-auth's loader has no typed declaration; explicit file only.
                    credentials, _ = load_credentials_from_file(  # type: ignore[no-untyped-call]
                        str(args.credentials),
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                    report.update(asyncio.run(run_smoke(profile, credentials, args.root)))
    except STTFailure as exc:
        report.update(status="FAILED", code=exc.code, provider_calls=None)
    except Exception:
        # Do not include exception text, transcript, credential or private filesystem paths.
        report.update(
            status="BLOCKED",
            blockers=["LOCAL_PREFLIGHT_OR_RUNTIME_FAILED"],
            provider_calls=None if args.execute else 0,
        )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
