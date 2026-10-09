"""Authoritative current source rights; frozen manifests remain immutable provenance."""

import json
import sqlite3
from dataclasses import dataclass
from uuid import UUID

from flowlens.sources.metadata import RightsProfile


@dataclass(frozen=True)
class SourcePolicy:
    rights: RightsProfile
    expires_ms: int


def policy(connection: sqlite3.Connection, session: UUID, source: UUID) -> SourcePolicy | None:
    if not connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name='platform_source_packages'"
    ).fetchone():
        return None
    package = connection.execute(
        "SELECT * FROM platform_source_packages WHERE session_id=? AND source_id=?",
        (str(session), str(source)),
    ).fetchone()
    if package is None:
        return None
    override = connection.execute(
        "SELECT payload FROM platform_source_rights WHERE session_id=? AND source_id=? "
        "ORDER BY version DESC LIMIT 1",
        (str(session), str(source)),
    ).fetchone()
    raw = (
        override["payload"]
        if override
        else json.dumps(json.loads(package["payload"])["declaration"]["rights"])
    )
    return SourcePolicy(RightsProfile.model_validate_json(raw), package["expires_ms"])
