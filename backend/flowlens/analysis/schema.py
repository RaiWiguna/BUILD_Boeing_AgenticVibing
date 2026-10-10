"""B-owned migrations. Parent run/revision references are supplied by the platform."""

from flowlens.core.modules import MigrationSpec

ANALYSIS_MIGRATIONS = (
    MigrationSpec(
        "analysis.0001",
        "B",
        ("platform.0001",),
        """
        CREATE TABLE analysis_configurations(
            id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL,
            run_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
            input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
            config_hash TEXT NOT NULL CHECK(length(config_hash)=64),
            payload TEXT NOT NULL CHECK(json_valid(payload)),
            UNIQUE(session_id,run_id,revision),
            FOREIGN KEY(session_id,revision)
                REFERENCES platform_revisions(session_id,revision),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
        """,
    ),
)
