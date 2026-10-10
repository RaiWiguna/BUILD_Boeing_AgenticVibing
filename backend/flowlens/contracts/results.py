"""Canonical accepted payload hash shared by API and database-free workers."""

import hashlib
import json

from flowlens.contracts.models import JobResult


def result_hash(result: JobResult) -> str:
    data = result.model_dump(mode="json")
    payload = {
        key: data[key]
        for key in ("outputs", "evidence", "artifacts", "status", "usage", "failure_code")
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
