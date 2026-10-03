"""Typed dependency boundaries for replay composition.

Ports are declarations only: importing this module does not create an archive,
start a worker, or open a connection. Domain-owned DTOs remain structural until
the Simulation/Detection and AI Harness contracts are available.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from .models import Clearance, SimulationConfig, Track
    from .replay_contracts import ReplayEventRecord, ReplaySourceManifest


class ReplayEventSource(Protocol):
    """Ordered, read-only source records for a single replay source."""

    def manifest(self) -> ReplaySourceManifest: ...

    def read(self, after_ordinal: int, until_ms: int | None = None) -> Sequence[ReplayEventRecord]: ...


class ReplayArchiveReader(Protocol):
    """Public source reader. Frame results contain public state only."""

    def metadata(self, source_session_id: str) -> Mapping[str, Any] | None: ...

    def frame(self, source_session_id: str, at_ms: int | None = None) -> Mapping[str, Any] | None: ...

    def events(
        self, source_session_id: str, after_ordinal: int = 0, until_ms: int | None = None
    ) -> Sequence[Mapping[str, Any]]: ...


class PrivateCheckpointReader(Protocol):
    """Separate internal capability for compatible synthetic branch state."""

    def checkpoint(self, source_session_id: str, at_ms: int) -> Mapping[str, Any] | None: ...


class SessionWriter(Protocol):
    """Current single-writer persistence operations used by Session.

    Implementations persist a frame and an optional command receipt in the
    same storage operation. Replay-import and assist transaction methods will
    be added by the owning BE tasks when those resources exist.
    """

    def create(self, session_id: str, metadata: dict[str, Any]) -> None: ...

    def save(
        self,
        session_id: str,
        status: str,
        events: list[dict[str, Any]],
        public_frame: dict[str, Any],
        private_checkpoint: dict[str, Any],
        command: tuple[str, dict[str, Any], dict[str, Any]] | None = None,
    ) -> None: ...

    def command(self, session_id: str, command_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None: ...


EventSink = Callable[..., dict[str, Any]]


class DetectorPort(Protocol):
    """Structural boundary for SD-owned detection results."""

    def evaluate(
        self,
        tracks: dict[str, Track],
        clearances: list[Clearance],
        now_ms: int,
        config: SimulationConfig,
        runway_open: bool,
        expected_ids: list[str],
        previous_tracks: dict[str, Track] | None = None,
    ) -> Mapping[str, Any]: ...


class AlertLifecyclePort(Protocol):
    """Pure lifecycle seam; persistence stays with SessionWriter."""

    def update(
        self,
        alerts: dict[str, dict[str, Any]],
        result: Mapping[str, Any],
        now_ms: int,
        emit_event: EventSink,
    ) -> None: ...


class WorkerRequest(Protocol):
    """Read-only structural request owned by the AI Harness workstream."""

    @property
    def job_id(self) -> str: ...

    @property
    def attempt_id(self) -> str: ...

    @property
    def asset_id(self) -> str: ...

    @property
    def local_asset_ref(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    @property
    def config_version(self) -> str: ...

    @property
    def public_evidence(self) -> Sequence[Mapping[str, Any]]: ...


class WorkerResult(Protocol):
    """Read-only typed worker output; it carries no persistence authority."""

    @property
    def job_id(self) -> str: ...

    @property
    def attempt_id(self) -> str: ...

    @property
    def asset_id(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    @property
    def config_version(self) -> str: ...

    @property
    def status(self) -> str: ...


RequestT_contra = TypeVar("RequestT_contra", bound=WorkerRequest, contravariant=True)
ResultT_co = TypeVar("ResultT_co", bound=WorkerResult, covariant=True)


class WorkerPort(Protocol, Generic[RequestT_contra, ResultT_co]):
    """Worker capability is limited to one typed request and typed result."""

    def process(self, request: RequestT_contra) -> ResultT_co: ...


class SessionWriterFactory(Protocol):
    def __call__(self, archive: SessionWriter) -> SessionWriter: ...


@dataclass(frozen=True)
class CompositionOverrides:
    """Optional test/runtime adapters consumed by the application composition root."""

    replay_event_source: ReplayEventSource | None = None
    replay_archive_reader: ReplayArchiveReader | None = None
    session_writer_factory: SessionWriterFactory | None = None
    detector: DetectorPort | None = None
    alert_lifecycle: AlertLifecyclePort | None = None
    worker: WorkerPort[Any, Any] | None = None


__all__ = [
    "AlertLifecyclePort",
    "CompositionOverrides",
    "DetectorPort",
    "EventSink",
    "PrivateCheckpointReader",
    "ReplayArchiveReader",
    "ReplayEventSource",
    "SessionWriter",
    "SessionWriterFactory",
    "WorkerPort",
    "WorkerRequest",
    "WorkerResult",
]
