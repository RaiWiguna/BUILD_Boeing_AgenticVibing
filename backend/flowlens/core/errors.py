"""Stable, safe errors. Untrusted exception text is never a public message."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

ErrorCode = Literal[
    "AUTH_REQUIRED",
    "ACCESS_DENIED",
    "INVALID_INPUT",
    "INVALID_IMPORT",
    "SOURCE_PERMISSION_REQUIRED",
    "CLOUD_TRANSFER_BLOCKED",
    "ALIGNMENT_REQUIRED",
    "NOT_EVALUABLE",
    "VERSION_CONFLICT",
    "IDEMPOTENCY_CONFLICT",
    "PROVIDER_UNAVAILABLE",
    "PROVIDER_QUOTA_EXCEEDED",
    "BUDGET_EXCEEDED",
    "INVALID_AI_OUTPUT",
    "SOURCE_REVISION_CHANGED",
    "EVIDENCE_UNAVAILABLE",
    "LEASE_EXPIRED",
    "JOB_CANCELLED",
]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: ErrorCode
    message: str
    request_id: str
    field_issues: list[str] = []
    recovery_hint: str = "Check permissions, input revision and request state."


class ContractError(Exception):
    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code)


HTTP_STATUS: dict[ErrorCode, int] = {
    "AUTH_REQUIRED": 401,
    "ACCESS_DENIED": 403,
    "INVALID_INPUT": 422,
    "INVALID_IMPORT": 422,
    "SOURCE_PERMISSION_REQUIRED": 403,
    "CLOUD_TRANSFER_BLOCKED": 403,
    "ALIGNMENT_REQUIRED": 422,
    "NOT_EVALUABLE": 422,
    "VERSION_CONFLICT": 409,
    "IDEMPOTENCY_CONFLICT": 409,
    "PROVIDER_UNAVAILABLE": 503,
    "PROVIDER_QUOTA_EXCEEDED": 429,
    "BUDGET_EXCEEDED": 429,
    "INVALID_AI_OUTPUT": 422,
    "SOURCE_REVISION_CHANGED": 409,
    "EVIDENCE_UNAVAILABLE": 404,
    "LEASE_EXPIRED": 409,
    "JOB_CANCELLED": 409,
}
