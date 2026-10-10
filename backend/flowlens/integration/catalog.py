"""Code-owned joint schema, factories and sensitive-table inventory."""

from flowlens.advisory.store import MIGRATIONS, SQLiteAdvisoryRepository
from flowlens.analysis.repository import SQLiteConfigurationRepository
from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.analysis.transcript_store import RECORDS, TRANSCRIPT_MIGRATIONS, factory
from flowlens.core.modules import MigrationSpec
from flowlens.memory.store import MEMORY_MIGRATIONS, SQLiteMemoryRepository
from flowlens.storage.sqlite.database import RepositoryFactory
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

PUBLIC = "analysis.accepted"
JOINT_MIGRATION = MigrationSpec(
    "analysis.0005",
    "B",
    ("analysis.0004", "platform.0018"),
    """
    CREATE TABLE analysis_public_records(
      id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
      revision INTEGER NOT NULL, kind TEXT NOT NULL,
      payload TEXT NOT NULL CHECK(json_valid(payload)),
      FOREIGN KEY(session_id,run_id,revision) REFERENCES platform_runs(session_id,id,revision));
    CREATE TABLE analysis_intent_submissions(
      attempt_id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
      revision INTEGER NOT NULL, result_hash TEXT NOT NULL,
      payload TEXT NOT NULL CHECK(json_valid(payload)),
      FOREIGN KEY(session_id,run_id,revision) REFERENCES platform_runs(session_id,id,revision));
    """,
)
B_MIGRATIONS = (
    *ANALYSIS_MIGRATIONS,
    *TRANSCRIPT_MIGRATIONS,
    *MEMORY_MIGRATIONS,
    *MIGRATIONS,
    JOINT_MIGRATION,
)
JOINT_MIGRATIONS = (*PLATFORM_MIGRATIONS, *B_MIGRATIONS)
TABLES = (
    "analysis_configurations",
    *(t for t, _ in RECORDS.values()),
    "analysis_memory_ledger",
    "analysis_advisory_ledger",
    "analysis_public_records",
    "analysis_intent_submissions",
)


def repositories() -> dict[str, RepositoryFactory]:
    from flowlens.integration.store import PublicRepository

    return {
        "analysis.configuration": SQLiteConfigurationRepository,
        **{n: factory(n) for n in RECORDS},
        "analysis.intent.memory": SQLiteMemoryRepository,
        "analysis.advisory": SQLiteAdvisoryRepository,
        PUBLIC: PublicRepository,
        "analysis.transcripts": PublicRepository,
    }
