"""Code-owned file inventory derived from snapshot rows, never caller paths."""

import sqlite3
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from flowlens.contracts.models import ArtifactSubmission
from flowlens.imports.metadata import PreparedImport
from flowlens.imports.staging import FilePreview, ImportPreview

Group = Literal["raw", "artifacts", "imports"]


@dataclass(frozen=True)
class Item:
    group: Group
    package: UUID
    filename: str
    session_id: UUID | None
    expires_ms: int
    file: FilePreview | None = None

    @property
    def path(self) -> str:
        return f"{self.group}/{self.package}/{self.filename}"


def catalog(connection: sqlite3.Connection, now: int) -> list[Item]:
    items = []
    for row in connection.execute("SELECT * FROM platform_source_packages ORDER BY package_id"):
        p = PreparedImport.model_validate_json(row["payload"])
        sid, package = UUID(row["session_id"]), UUID(row["package_id"])
        items.append(Item("raw", package, "inventory.json", sid, row["expires_ms"]))
        items.extend(
            Item("raw", package, f"{f.id}.raw", sid, row["expires_ms"], f) for f in p.files
        )
    for row in connection.execute(
        "SELECT * FROM platform_artifact_staging WHERE expires_ms>? ORDER BY id", (now,)
    ):
        # Both accepted and sealed pending references belong to the selected DB point.
        ArtifactSubmission.model_validate_json(row["spec"])
        f = FilePreview.model_validate_json(row["facts"])
        sid, package = UUID(row["session_id"]), UUID(row["package_id"])
        items.append(Item("artifacts", package, "inventory.json", sid, row["expires_ms"]))
        items.append(Item("artifacts", package, f"{f.id}.raw", sid, row["expires_ms"], f))
    for row in connection.execute(
        "SELECT * FROM platform_import_drafts WHERE status='NEEDS_REMEDIATION' "
        "AND expires_ms>? AND payload IS NOT NULL ORDER BY id",
        (now,),
    ):
        preview = ImportPreview.model_validate_json(row["payload"])
        reference = connection.execute(
            "SELECT s.session_id,s.expires_ms FROM platform_import_commits c "
            "JOIN platform_source_packages s ON s.package_id=c.package_id WHERE c.draft_id=?",
            (row["id"],),
        ).fetchone()
        draft_session = UUID(reference[0]) if reference else None
        expiry = min(row["expires_ms"], reference[1]) if reference else row["expires_ms"]
        items.extend(
            Item("imports", preview.id, f"{f.id}.upload", draft_session, expiry, f)
            for f in preview.files
        )
    if len({i.path for i in items}) != len(items):
        raise ValueError("Duplicate snapshot file identity")
    return items
