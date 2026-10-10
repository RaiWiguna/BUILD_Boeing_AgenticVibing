"""API-side foundation service and frozen registration entrypoint."""

from typing import cast
from uuid import UUID, uuid4

from flowlens.analysis.config import AnalysisConfig, ConfigurationRecord
from flowlens.analysis.repository import (
    NAMESPACE,
    ConfigurationRepository,
    SQLiteConfigurationRepository,
)
from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.contracts.models import JobResult, RequestContext, Snapshot
from flowlens.contracts.ports import AnalysisModule, EvidenceService, TransactionFactory, UnitOfWork
from flowlens.core.errors import ContractError
from flowlens.core.modules import ModuleRegistration


class AnalysisFoundation:
    def __init__(self, config: AnalysisConfig, transactions: TransactionFactory) -> None:
        self.config = AnalysisConfig.model_validate_json(config.model_dump_json())
        self.transactions = transactions

    def configure(self, context: RequestContext, uow: UnitOfWork) -> UUID:
        context.require("analysis", context.session_id, context.analysis_run_id)
        if context.analysis_run_id is None:
            raise ContractError("INVALID_INPUT")
        record = ConfigurationRecord(
            id=uuid4(),
            session_id=context.session_id,
            analysis_run_id=context.analysis_run_id,
            revision=context.input_revision,
            input_hash=context.input_hash,
            config=self.config,
            config_hash=self.config.digest(),
        )
        identifier = uow.repository(NAMESPACE).append(context, record)
        uow.audit(context, "ANALYSIS_CONFIGURED", identifier)
        uow.enqueue_event(context, record)
        return identifier

    def inventory(self, context: RequestContext) -> list[ConfigurationRecord]:
        with self.transactions.begin() as uow:
            return cast(ConfigurationRepository, uow.repository(NAMESPACE)).inventory(context)

    def purge(self, context: RequestContext, uow: UnitOfWork) -> None:
        context.require("admin", context.session_id, context.analysis_run_id)
        cast(ConfigurationRepository, uow.repository(NAMESPACE)).purge(context)
        uow.audit(context, "ANALYSIS_CONFIG_PURGED", context.session_id)

    def ready(self) -> bool:
        return False

    def validate(
        self, context: RequestContext, candidate: JobResult, evidence: EvidenceService
    ) -> JobResult:
        context.require("analysis", candidate.session_id, candidate.analysis_run_id)
        raise ContractError("NOT_EVALUABLE")

    def accept(self, context: RequestContext, validated: JobResult, uow: UnitOfWork) -> None:
        context.require("analysis", validated.session_id, validated.analysis_run_id)
        raise ContractError("NOT_EVALUABLE")

    def snapshot(self, context: RequestContext) -> Snapshot:
        context.require("read", context.session_id, context.analysis_run_id)
        raise ContractError("NOT_EVALUABLE")


def register_analysis(
    config: AnalysisConfig, transactions: TransactionFactory
) -> ModuleRegistration:
    mock = getattr(transactions, "profile", None) == "MOCK"
    if config.profile == "production" and mock:
        raise ValueError("MOCK transaction adapter forbidden in production.")
    service = AnalysisFoundation(config, transactions)
    analysis: AnalysisModule = service
    return ModuleRegistration(
        name="analysis",
        mock=mock,
        services={"analysis": analysis, "analysis_inventory": service.inventory},
        repositories={NAMESPACE: SQLiteConfigurationRepository},
        migrations=ANALYSIS_MIGRATIONS,
        purge_handler=service.purge,
        readiness=service.ready,
        config_keys=tuple(AnalysisConfig.model_fields),
        inventory_namespaces=(NAMESPACE,),
        # Snapshot and worker handlers are intentionally absent until implemented.
    )
