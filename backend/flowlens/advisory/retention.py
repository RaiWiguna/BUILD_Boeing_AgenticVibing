"""Analysis-only inventory/purge orchestration in a caller-owned transaction."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from flowlens.contracts.models import Contract, RequestContext
from flowlens.contracts.ports import UnitOfWork
from flowlens.core.errors import ContractError


@dataclass(frozen=True)
class RetentionPort:
    namespace: str
    inventory: Callable[[RequestContext, UnitOfWork], Sequence[Contract]]
    purge: Callable[[RequestContext, UnitOfWork], None]


class AnalysisRetention:
    """Caller supplies registered B participants in dependency-safe purge order.

    This never handles platform assets, artifact TTL/promotion, audit erasure or
    tombstones. Durable retention authority is required even for an empty inventory.
    """

    def __init__(
        self,
        ports: tuple[RetentionPort, ...],
        authorize: Callable[[RequestContext, str, UnitOfWork], None],
    ) -> None:
        names = [p.namespace for p in ports]
        if (
            not ports
            or len(set(names)) != len(names)
            or any(not name.startswith("analysis.") for name in names)
        ):
            raise ContractError("INVALID_INPUT")
        self.ports, self.authorize = ports, authorize

    def inventory(self, ctx: RequestContext, uow: UnitOfWork) -> dict[str, int]:
        ctx.require("admin", ctx.session_id, ctx.analysis_run_id)
        self.authorize(ctx, "INVENTORY", uow)
        return {p.namespace: len(p.inventory(ctx, uow)) for p in self.ports}

    def purge(self, ctx: RequestContext, uow: UnitOfWork) -> dict[str, int]:
        before = self.inventory(ctx, uow)
        self.authorize(ctx, "PURGE", uow)
        for port in self.ports:
            port.purge(ctx, uow)
        if any(p.inventory(ctx, uow) for p in self.ports):
            raise ContractError("VERSION_CONFLICT")
        uow.audit(ctx, "ANALYSIS_RETENTION_PURGED", ctx.session_id)
        return before
