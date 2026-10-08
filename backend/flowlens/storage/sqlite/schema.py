"""Platform-owned relational foundation; domain lifecycles arrive in owner units."""

from flowlens.core.modules import MigrationSpec

PLATFORM_MIGRATIONS = (
    MigrationSpec(
        "platform.0001",
        "A",
        (),
        """
        CREATE TABLE platform_accounts(
            id TEXT PRIMARY KEY NOT NULL, login TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL, active INTEGER NOT NULL CHECK(active IN (0,1)));
        CREATE TABLE platform_sessions(id TEXT PRIMARY KEY NOT NULL);
        CREATE TABLE platform_revisions(
            session_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
            input_hash TEXT NOT NULL CHECK(length(input_hash)=64),
            PRIMARY KEY(session_id,revision),
            FOREIGN KEY(session_id) REFERENCES platform_sessions(id));
        CREATE TABLE platform_runs(
            session_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
            PRIMARY KEY(session_id,id), UNIQUE(session_id,id,revision),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision));
        CREATE TABLE platform_grants(
            account_id TEXT NOT NULL, session_id TEXT NOT NULL, capability TEXT NOT NULL,
            PRIMARY KEY(account_id,session_id,capability),
            FOREIGN KEY(account_id) REFERENCES platform_accounts(id),
            FOREIGN KEY(session_id) REFERENCES platform_sessions(id));
    """,
    ),
    MigrationSpec(
        "platform.0002",
        "A",
        ("platform.0001",),
        """
        CREATE TABLE platform_sources(
            session_id TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
            source_hash TEXT NOT NULL CHECK(length(source_hash)=64), payload TEXT NOT NULL,
            PRIMARY KEY(session_id,id,revision),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision));
        CREATE TABLE platform_assets(
            session_id TEXT NOT NULL, id TEXT NOT NULL, source_id TEXT NOT NULL,
            revision INTEGER NOT NULL, storage_key TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL CHECK(length(sha256)=64),
            PRIMARY KEY(session_id,id),
            FOREIGN KEY(session_id,source_id,revision)
                REFERENCES platform_sources(session_id,id,revision));
        CREATE TABLE platform_jobs(
            session_id TEXT NOT NULL, id TEXT NOT NULL, run_id TEXT NOT NULL,
            revision INTEGER NOT NULL, PRIMARY KEY(session_id,id),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
        CREATE TABLE platform_attempts(
            session_id TEXT NOT NULL, id TEXT NOT NULL, job_id TEXT NOT NULL,
            lease_id TEXT UNIQUE, PRIMARY KEY(session_id,id),
            FOREIGN KEY(session_id,job_id) REFERENCES platform_jobs(session_id,id));
        CREATE TABLE platform_receipts(
            session_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
            request_hash TEXT NOT NULL CHECK(length(request_hash)=64), payload TEXT NOT NULL,
            PRIMARY KEY(session_id,attempt_id),
            FOREIGN KEY(session_id,attempt_id) REFERENCES platform_attempts(session_id,id));
        CREATE TABLE platform_records(
            namespace TEXT NOT NULL, id TEXT NOT NULL, session_id TEXT NOT NULL,
            run_id TEXT, revision INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(namespace,id),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
        CREATE TABLE platform_evidence(
            namespace TEXT NOT NULL, id TEXT NOT NULL, session_id TEXT NOT NULL,
            run_id TEXT, revision INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
            source_id TEXT NOT NULL, PRIMARY KEY(namespace,id),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision),
            FOREIGN KEY(session_id,source_id,revision)
                REFERENCES platform_sources(session_id,id,revision));
        CREATE TABLE platform_events(
            session_id TEXT NOT NULL, sequence INTEGER NOT NULL CHECK(sequence>0),
            run_id TEXT, revision INTEGER NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(session_id,sequence),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
        CREATE TABLE platform_audit(
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, actor_id TEXT NOT NULL,
            request_id TEXT NOT NULL, action TEXT NOT NULL, target_id TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES platform_sessions(id));
        CREATE TABLE platform_replay(
            session_id TEXT NOT NULL, revision INTEGER NOT NULL,
            checkpoint_ms INTEGER NOT NULL CHECK(checkpoint_ms>=0),
            reducer_version TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(session_id,revision,checkpoint_ms,reducer_version),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision));
        CREATE TABLE platform_artifacts(
            session_id TEXT NOT NULL, id TEXT NOT NULL, run_id TEXT,
            revision INTEGER NOT NULL, storage_key TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
            PRIMARY KEY(session_id,id),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
    """,
    ),
    MigrationSpec(
        "platform.0003",
        "A",
        ("platform.0002",),
        """
        CREATE TABLE platform_legacy_imports(
            digest TEXT PRIMARY KEY NOT NULL CHECK(length(digest)=64),
            profile TEXT NOT NULL, counts TEXT NOT NULL);
        CREATE TABLE platform_legacy_sessions(
            legacy_id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL UNIQUE,
            digest TEXT NOT NULL, metadata TEXT NOT NULL, original_status TEXT NOT NULL,
            runtime_status TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES platform_sessions(id),
            FOREIGN KEY(digest) REFERENCES platform_legacy_imports(digest));
        CREATE TABLE platform_legacy_events(
            session_id TEXT NOT NULL REFERENCES platform_legacy_sessions(legacy_id),
            ordinal INTEGER NOT NULL CHECK(ordinal>=1), data TEXT NOT NULL,
            PRIMARY KEY(session_id,ordinal));
        CREATE TABLE platform_legacy_frames(
            session_id TEXT NOT NULL REFERENCES platform_legacy_sessions(legacy_id),
            sim_ms INTEGER NOT NULL CHECK(sim_ms>=0), sequence INTEGER NOT NULL CHECK(sequence>=0),
            public TEXT NOT NULL, PRIMARY KEY(session_id,sim_ms));
        CREATE TABLE platform_legacy_private_frames(
            session_id TEXT NOT NULL, sim_ms INTEGER NOT NULL, private TEXT NOT NULL,
            PRIMARY KEY(session_id,sim_ms),
            FOREIGN KEY(session_id,sim_ms) REFERENCES platform_legacy_frames(session_id,sim_ms));
        CREATE TABLE platform_legacy_commands(
            session_id TEXT NOT NULL REFERENCES platform_legacy_sessions(legacy_id),
            command_id TEXT NOT NULL, request TEXT NOT NULL, response TEXT NOT NULL,
            PRIMARY KEY(session_id,command_id));
    """,
    ),
    MigrationSpec(
        "platform.0004",
        "A",
        ("platform.0003",),
        """
        ALTER TABLE platform_accounts ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0
            CHECK(is_admin IN (0,1));
        ALTER TABLE platform_accounts ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 1
            CHECK(must_change_password IN (0,1));
        ALTER TABLE platform_accounts ADD COLUMN credential_version INTEGER NOT NULL DEFAULT 1
            CHECK(credential_version>=1);
        CREATE TABLE platform_security_state(name TEXT PRIMARY KEY NOT NULL,value TEXT NOT NULL);
        CREATE TABLE platform_account_audit(
            id INTEGER PRIMARY KEY, actor_id TEXT REFERENCES platform_accounts(id),
            target_id TEXT NOT NULL REFERENCES platform_accounts(id),
            action TEXT NOT NULL, recorded_at TEXT NOT NULL);
    """,
    ),
    MigrationSpec(
        "platform.0005",
        "A",
        ("platform.0004",),
        """
        CREATE TABLE platform_auth_sessions(
            token_hash TEXT PRIMARY KEY NOT NULL CHECK(length(token_hash)=64),
            account_id TEXT NOT NULL REFERENCES platform_accounts(id),
            credential_version INTEGER NOT NULL CHECK(credential_version>=1),
            created_ms INTEGER NOT NULL CHECK(created_ms>=0),
            last_seen_ms INTEGER NOT NULL CHECK(last_seen_ms>=created_ms),
            expires_ms INTEGER NOT NULL CHECK(expires_ms>created_ms),
            revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)));
        CREATE INDEX platform_auth_account ON platform_auth_sessions(account_id);
        CREATE TABLE platform_login_limits(
            key_digest TEXT PRIMARY KEY NOT NULL CHECK(length(key_digest)=64),
            window_ms INTEGER NOT NULL CHECK(window_ms>=0),
            attempts INTEGER NOT NULL CHECK(attempts>=1));
    """,
    ),
)
