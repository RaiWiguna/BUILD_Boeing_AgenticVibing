"""Package B API-side foundation; worker/provider implementations are separate units."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flowlens.analysis.config import AnalysisConfig
    from flowlens.contracts.ports import TransactionFactory
    from flowlens.core.modules import ModuleRegistration


def register_analysis(
    config: "AnalysisConfig", transactions: "TransactionFactory"
) -> "ModuleRegistration":
    # Importing private record models in a provider must not load API database writers.
    from flowlens.analysis.module import register_analysis as register

    return register(config, transactions)


__all__ = ["register_analysis"]
