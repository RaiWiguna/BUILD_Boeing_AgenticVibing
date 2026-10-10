"""Authenticated HTTP ports. This worker module never imports SQLite or API services."""

from collections.abc import Iterator
from uuid import UUID

import httpx

from flowlens.audio.process import AudioError
from flowlens.contracts.models import (
    ArtifactSubmission,
    CommitReceipt,
    JobLease,
    JobResult,
    RequestContext,
)
from flowlens.workers.audio.models import AudioInput


class AudioPorts:
    def __init__(self, client: httpx.Client, token: str) -> None:
        self.client = client
        self.headers = {"Authorization": "Bearer " + token}
        self.scope: UUID | None = None
        self.binding: AudioInput | None = None

    def request(self, method: str, path: str, *, json: object) -> httpx.Response:
        response = self.client.request(method, path, headers=self.headers, json=json)
        if response.is_error:
            try:
                code = response.json()["code"]
            except (ValueError, KeyError):
                code = "NOT_EVALUABLE"
            raise AudioError(code)
        return response

    def lease(self, worker_id: UUID, stage: str) -> JobLease | None:
        data = self.request("POST", "/internal/jobs/lease", json={"stage": stage}).json()
        if data["lease"] is None:
            return None
        lease = JobLease.model_validate_json(__import__("json").dumps(data["lease"]))
        if lease.owner_id != worker_id:
            raise AudioError("ACCESS_DENIED")
        self.scope = UUID(data["scope_id"])
        return lease

    def resolve(self, lease: JobLease) -> AudioInput:
        response = self.request(
            "POST", "/internal/analysis/audio-input", json=lease.model_dump(mode="json")
        )
        self.binding = AudioInput.model_validate_json(response.content)
        return self.binding

    def heartbeat(self, lease: JobLease) -> JobLease:
        return JobLease.model_validate_json(
            self.request(
                "POST",
                f"/internal/jobs/{lease.job_id}/heartbeat",
                json=lease.model_dump(mode="json"),
            ).content
        )

    def cancelled(self, lease: JobLease) -> bool:
        return bool(
            self.request(
                "POST",
                f"/internal/jobs/{lease.job_id}/cancelled",
                json=lease.model_dump(mode="json"),
            ).json()["cancelled"]
        )

    def result(self, result: JobResult) -> CommitReceipt:
        return CommitReceipt.model_validate_json(
            self.request(
                "POST",
                f"/internal/jobs/{result.job_id}/results",
                json=result.model_dump(mode="json"),
            ).content
        )

    def download(self, context: RequestContext, asset_id: UUID, start: int, end: int) -> bytes:
        if (
            self.binding is None
            or context != self.binding.context
            or asset_id != self.binding.asset.id
        ):
            raise AudioError("ACCESS_DENIED")
        response = self.client.get(
            f"/internal/assets/{asset_id}/audio",
            params={"scope_id": str(self.scope)},
            headers={**self.headers, "Range": f"bytes={start}-{end - 1}"},
        )
        if response.status_code != 206 or len(response.content) != end - start:
            raise AudioError("ACCESS_DENIED")
        return response.content

    def submit(
        self, context: RequestContext, artifact: ArtifactSubmission, chunks: Iterator[bytes]
    ) -> UUID:
        if self.binding is None or context != self.binding.context:
            raise AudioError("ACCESS_DENIED")
        response = self.client.put(
            f"/internal/artifacts/{artifact.id}",
            params={"scope_id": str(self.scope)},
            headers={
                **self.headers,
                "Content-Type": "application/octet-stream",
                "X-Artifact-Metadata": artifact.model_dump_json(),
            },
            content=chunks,
        )
        if response.is_error:
            raise AudioError("INVALID_INPUT")
        return UUID(response.json()["id"])
