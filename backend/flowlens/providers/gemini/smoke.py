"""Fail-closed readiness inspection. No implicit credential lookup or network calls."""

import json

from flowlens.contracts.models import Contract
from flowlens.providers.gemini.models import GeminiConfig
from pydantic import Field


class SmokeApproval(Contract):
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    identity_verified: bool
    model_api_access_verified: bool
    quota_verified: bool
    synthetic_cloud_rights_verified: bool
    terms_retention_approved: bool
    paid_request_approved: bool
    budget_microunits: int = Field(ge=0)


def preflight(
    config: GeminiConfig,
    approval: SmokeApproval | None = None,
    *,
    credential_present: bool = False,
) -> tuple[str, ...]:
    blockers = []
    if config.profile != "GOOGLE":
        blockers.append("REAL_PROFILE_REQUIRED")
    if not credential_present:
        blockers.append("GEMINI_CREDENTIAL_REQUIRED")
    if approval is None or approval.config_hash != config.digest():
        blockers.append("BOUND_APPROVAL_REQUIRED")
    if approval is not None:
        for verified, reason in (
            (approval.identity_verified, "IDENTITY_UNVERIFIED"),
            (approval.model_api_access_verified, "MODEL_API_ACCOUNT_ACCESS_UNVERIFIED"),
            (approval.quota_verified, "QUOTA_UNVERIFIED"),
            (approval.synthetic_cloud_rights_verified, "CLOUD_RIGHTS_UNVERIFIED"),
            (approval.terms_retention_approved, "TERMS_RETENTION_UNAPPROVED"),
            (approval.paid_request_approved, "PAID_REQUEST_UNAPPROVED"),
            (approval.budget_microunits > 0, "BUDGET_REQUIRED"),
        ):
            if not verified:
                blockers.append(reason)
    return tuple(blockers)


def main() -> None:
    print(
        json.dumps(
            {
                "unit": "B04",
                "status": "BLOCKED",
                "provider_calls": 0,
                "external_acceptance": "GEMINI_EXTERNAL_ACCEPTANCE_PENDING",
                "blockers": preflight(GeminiConfig()),
                "benchmark_metrics": None,
                "pipeline_ready": False,
            }
        )
    )


if __name__ == "__main__":
    main()
