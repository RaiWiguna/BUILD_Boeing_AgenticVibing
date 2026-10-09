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
    MigrationSpec(
        "platform.0006",
        "A",
        ("platform.0005",),
        """
        ALTER TABLE platform_grants ADD COLUMN role TEXT NOT NULL DEFAULT 'observer'
            CHECK(role IN ('observer','controller','evaluator'));
        ALTER TABLE platform_grants ADD COLUMN expires_ms INTEGER CHECK(expires_ms>=0);
        ALTER TABLE platform_grants ADD COLUMN revoked INTEGER NOT NULL DEFAULT 0
            CHECK(revoked IN (0,1));
        CREATE TABLE platform_context_state(
            session_id TEXT PRIMARY KEY NOT NULL REFERENCES platform_sessions(id),
            as_of_ms INTEGER NOT NULL CHECK(as_of_ms>=0),
            mode TEXT NOT NULL CHECK(mode IN ('AS_KNOWN','DEBRIEF')));
        CREATE TABLE platform_workers(
            id TEXT PRIMARY KEY NOT NULL, token_hash TEXT NOT NULL UNIQUE,
            expires_ms INTEGER NOT NULL CHECK(expires_ms>=0),
            revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)));
        CREATE TABLE platform_worker_scopes(
            id TEXT PRIMARY KEY NOT NULL, worker_id TEXT NOT NULL REFERENCES platform_workers(id),
            session_id TEXT NOT NULL, run_id TEXT NOT NULL, revision INTEGER NOT NULL,
            as_of_ms INTEGER NOT NULL CHECK(as_of_ms>=0),
            expires_ms INTEGER NOT NULL CHECK(expires_ms>=0),
            revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
        CREATE TABLE platform_worker_sources(
            scope_id TEXT NOT NULL REFERENCES platform_worker_scopes(id),
            session_id TEXT NOT NULL, source_id TEXT NOT NULL, revision INTEGER NOT NULL,
            PRIMARY KEY(scope_id,source_id),
            FOREIGN KEY(session_id,source_id,revision)
                REFERENCES platform_sources(session_id,id,revision));
        CREATE TABLE platform_worker_assets(
            scope_id TEXT NOT NULL REFERENCES platform_worker_scopes(id),
            session_id TEXT NOT NULL, asset_id TEXT NOT NULL,
            PRIMARY KEY(scope_id,asset_id),
            FOREIGN KEY(session_id,asset_id) REFERENCES platform_assets(session_id,id));
        CREATE TABLE platform_context_receipts(
            digest TEXT PRIMARY KEY NOT NULL, principal_kind TEXT NOT NULL
                CHECK(principal_kind IN ('HUMAN','WORKER')),
            credential_hash TEXT NOT NULL, scope_id TEXT REFERENCES platform_worker_scopes(id),
            created_ms INTEGER NOT NULL CHECK(created_ms>=0),
            expires_ms INTEGER NOT NULL CHECK(expires_ms>created_ms));
        CREATE TABLE platform_permission_audit(
            id INTEGER PRIMARY KEY, actor_id TEXT NOT NULL REFERENCES platform_accounts(id),
            target_id TEXT NOT NULL, action TEXT NOT NULL, recorded_ms INTEGER NOT NULL);
        """,
    ),
    MigrationSpec(
        "platform.0007",
        "A",
        ("platform.0006",),
        """
        CREATE TABLE platform_mutation_versions(
            session_id TEXT NOT NULL, run_scope TEXT NOT NULL, run_id TEXT,
            namespace TEXT NOT NULL, target_id TEXT NOT NULL,
            version INTEGER NOT NULL CHECK(version>=1),
            CHECK(run_scope=COALESCE(run_id,'')),
            PRIMARY KEY(session_id,run_scope,namespace,target_id),
            FOREIGN KEY(session_id) REFERENCES platform_sessions(id),
            FOREIGN KEY(session_id,run_id) REFERENCES platform_runs(session_id,id));
        CREATE TABLE platform_mutation_receipts(
            id TEXT NOT NULL UNIQUE, session_id TEXT NOT NULL, run_scope TEXT NOT NULL, run_id TEXT,
            revision INTEGER NOT NULL, actor_id TEXT NOT NULL, operation TEXT NOT NULL,
            namespace TEXT NOT NULL, target_id TEXT NOT NULL,
            key_hash TEXT NOT NULL CHECK(length(key_hash)=64),
            request_hash TEXT NOT NULL CHECK(length(request_hash)=64),
            version INTEGER NOT NULL CHECK(version>=1),
            sequence INTEGER NOT NULL CHECK(sequence>=1),
            record_id TEXT NOT NULL, audit_id INTEGER NOT NULL REFERENCES platform_audit(id),
            CHECK(run_scope=COALESCE(run_id,'')),
            PRIMARY KEY(session_id,run_scope,actor_id,operation,target_id,key_hash),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision),
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision),
            FOREIGN KEY(session_id,run_scope,namespace,target_id)
                REFERENCES platform_mutation_versions(session_id,run_scope,namespace,target_id),
            FOREIGN KEY(session_id,sequence) REFERENCES platform_events(session_id,sequence));
        CREATE TRIGGER platform_append_only_platform_audit_update
            BEFORE UPDATE ON platform_audit BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_audit_delete
            BEFORE DELETE ON platform_audit BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_audit_replace
            BEFORE INSERT ON platform_audit
            WHEN EXISTS(SELECT 1 FROM platform_audit WHERE id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_account_audit_update
            BEFORE UPDATE ON platform_account_audit BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_account_audit_delete
            BEFORE DELETE ON platform_account_audit BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_account_audit_replace
            BEFORE INSERT ON platform_account_audit
            WHEN EXISTS(SELECT 1 FROM platform_account_audit WHERE id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_permission_audit_update
            BEFORE UPDATE ON platform_permission_audit BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_permission_audit_delete
            BEFORE DELETE ON platform_permission_audit BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_permission_audit_replace
            BEFORE INSERT ON platform_permission_audit
            WHEN EXISTS(SELECT 1 FROM platform_permission_audit WHERE id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_mutation_receipts_update
            BEFORE UPDATE ON platform_mutation_receipts BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_mutation_receipts_delete
            BEFORE DELETE ON platform_mutation_receipts BEGIN
            SELECT RAISE(ABORT,'Append-only record.'); END;
        CREATE TRIGGER platform_append_only_platform_mutation_receipts_replace
            BEFORE INSERT ON platform_mutation_receipts
            WHEN EXISTS(SELECT 1 FROM platform_mutation_receipts WHERE id=NEW.id)
              OR EXISTS(SELECT 1 FROM platform_mutation_receipts
                WHERE session_id=NEW.session_id AND run_scope=NEW.run_scope
                  AND actor_id=NEW.actor_id AND operation=NEW.operation
                  AND target_id=NEW.target_id AND key_hash=NEW.key_hash)
            BEGIN SELECT RAISE(ABORT,'Append-only record.'); END;
        """,
    ),
    MigrationSpec(
        "platform.0008",
        "A",
        ("platform.0007",),
        """
        CREATE TABLE platform_import_drafts(
            id TEXT PRIMARY KEY NOT NULL,
            owner_id TEXT NOT NULL REFERENCES platform_accounts(id),
            key_hash TEXT, request_hash TEXT,
            status TEXT NOT NULL CHECK(status IN ('UPLOADING','NEEDS_REMEDIATION','FAILED')),
            expires_ms INTEGER NOT NULL CHECK(expires_ms>=0), payload TEXT,
            UNIQUE(owner_id,key_hash));
        """,
    ),
    MigrationSpec(
        "platform.0009",
        "A",
        ("platform.0008",),
        """
        CREATE TABLE platform_import_metadata(
            draft_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0 AND revision<=64),
            actor_id TEXT NOT NULL, key_hash TEXT NOT NULL, request_hash TEXT NOT NULL,
            content_hash TEXT NOT NULL, declared_ms INTEGER NOT NULL CHECK(declared_ms>=0),
            payload TEXT NOT NULL,
            PRIMARY KEY(draft_id,revision), UNIQUE(draft_id,key_hash),
            FOREIGN KEY(draft_id) REFERENCES platform_import_drafts(id) ON DELETE CASCADE,
            FOREIGN KEY(actor_id) REFERENCES platform_accounts(id));
        CREATE TRIGGER platform_append_only_import_metadata_update
            BEFORE UPDATE ON platform_import_metadata BEGIN
            SELECT RAISE(ABORT,'Immutable import revision.'); END;
        CREATE TRIGGER platform_append_only_import_metadata_delete
            BEFORE DELETE ON platform_import_metadata
            WHEN EXISTS(SELECT 1 FROM platform_import_drafts WHERE id=OLD.draft_id)
            BEGIN SELECT RAISE(ABORT,'Immutable import revision.'); END;
        CREATE TRIGGER platform_append_only_import_metadata_replace
            BEFORE INSERT ON platform_import_metadata
            WHEN EXISTS(SELECT 1 FROM platform_import_metadata
                WHERE draft_id=NEW.draft_id AND (revision=NEW.revision OR key_hash=NEW.key_hash))
            BEGIN SELECT RAISE(ABORT,'Immutable import revision.'); END;
        """,
    ),
    MigrationSpec(
        "platform.0010",
        "A",
        ("platform.0009",),
        """
        CREATE TABLE platform_source_packages(
            package_id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL UNIQUE,
            source_id TEXT NOT NULL, revision INTEGER NOT NULL, owner_id TEXT NOT NULL,
            identity_hash TEXT NOT NULL, semantic_hash TEXT NOT NULL,
            committed_ms INTEGER NOT NULL, expires_ms INTEGER NOT NULL, payload TEXT NOT NULL,
            UNIQUE(owner_id,identity_hash),
        FOREIGN KEY(session_id,source_id,revision) REFERENCES
            platform_sources(session_id,id,revision),
            FOREIGN KEY(owner_id) REFERENCES platform_accounts(id));
        CREATE TABLE platform_import_commits(
            owner_id TEXT NOT NULL, draft_id TEXT NOT NULL, key_hash TEXT NOT NULL,
        request_hash TEXT NOT NULL, package_id TEXT NOT NULL REFERENCES
            platform_source_packages(package_id),
            payload TEXT NOT NULL, PRIMARY KEY(owner_id,draft_id,key_hash));
        CREATE TABLE platform_source_rights(
            session_id TEXT NOT NULL, source_id TEXT NOT NULL, version INTEGER NOT NULL,
            actor_id TEXT NOT NULL REFERENCES platform_accounts(id), recorded_ms INTEGER NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(session_id,source_id,version),
            FOREIGN KEY(session_id) REFERENCES platform_sessions(id));
        CREATE TRIGGER platform_append_only_source_rights_update BEFORE UPDATE ON
            platform_source_rights
            BEGIN SELECT RAISE(ABORT,'Immutable rights revision.'); END;
        CREATE TRIGGER platform_append_only_source_rights_delete BEFORE DELETE ON
            platform_source_rights
            BEGIN SELECT RAISE(ABORT,'Immutable rights revision.'); END;
        CREATE TRIGGER platform_append_only_source_rights_replace BEFORE INSERT ON
            platform_source_rights
        WHEN EXISTS(SELECT 1 FROM platform_source_rights WHERE session_id=NEW.session_id
            AND source_id=NEW.source_id AND version=NEW.version)
            BEGIN SELECT RAISE(ABORT,'Immutable rights revision.'); END;
        CREATE TRIGGER platform_append_only_source_package_update BEFORE UPDATE ON
            platform_source_packages
            BEGIN SELECT RAISE(ABORT,'Immutable source package.'); END;
        CREATE TRIGGER platform_append_only_source_package_delete BEFORE DELETE ON
            platform_source_packages
            BEGIN SELECT RAISE(ABORT,'Immutable source package.'); END;
        CREATE TRIGGER platform_append_only_source_package_replace BEFORE INSERT ON
            platform_source_packages
        WHEN EXISTS(SELECT 1 FROM platform_source_packages WHERE
            package_id=NEW.package_id OR session_id=NEW.session_id OR
            (owner_id=NEW.owner_id AND identity_hash=NEW.identity_hash))
            BEGIN SELECT RAISE(ABORT,'Immutable source package.'); END;
        CREATE TRIGGER platform_append_only_import_commit_update BEFORE UPDATE ON
            platform_import_commits
            BEGIN SELECT RAISE(ABORT,'Immutable import receipt.'); END;
        CREATE TRIGGER platform_append_only_import_commit_delete BEFORE DELETE ON
            platform_import_commits
            BEGIN SELECT RAISE(ABORT,'Immutable import receipt.'); END;
        CREATE TRIGGER platform_append_only_import_commit_replace BEFORE INSERT ON
            platform_import_commits
        WHEN EXISTS(SELECT 1 FROM platform_import_commits WHERE owner_id=NEW.owner_id
            AND draft_id=NEW.draft_id AND key_hash=NEW.key_hash)
            BEGIN SELECT RAISE(ABORT,'Immutable import receipt.'); END;
        CREATE TRIGGER platform_append_only_committed_source_update BEFORE UPDATE ON
            platform_sources
        WHEN EXISTS(SELECT 1 FROM platform_source_packages WHERE
            session_id=OLD.session_id AND source_id=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Immutable source.'); END;
        CREATE TRIGGER platform_append_only_committed_source_delete BEFORE DELETE ON
            platform_sources
        WHEN EXISTS(SELECT 1 FROM platform_source_packages WHERE
            session_id=OLD.session_id AND source_id=OLD.id)
            BEGIN SELECT RAISE(ABORT,'Immutable source.'); END;
        CREATE TRIGGER platform_append_only_committed_record_update BEFORE UPDATE ON
            platform_records
        WHEN OLD.namespace IN ('source_events','tracks') AND EXISTS(SELECT 1 FROM
            platform_source_packages WHERE session_id=OLD.session_id)
            BEGIN SELECT RAISE(ABORT,'Immutable observation.'); END;
        CREATE TRIGGER platform_append_only_committed_record_delete BEFORE DELETE ON
            platform_records
        WHEN OLD.namespace IN ('source_events','tracks') AND EXISTS(SELECT 1 FROM
            platform_source_packages WHERE session_id=OLD.session_id)
            BEGIN SELECT RAISE(ABORT,'Immutable observation.'); END;

            CREATE TRIGGER platform_append_only_committed_source_replace
            BEFORE INSERT ON platform_sources
            WHEN EXISTS(SELECT 1 FROM platform_source_packages
                WHERE session_id=NEW.session_id AND source_id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Immutable source.'); END;
        CREATE TRIGGER platform_append_only_committed_record_replace
            BEFORE INSERT ON platform_records
            WHEN EXISTS(SELECT 1 FROM platform_records r
                JOIN platform_source_packages p ON p.session_id=r.session_id
                WHERE r.namespace IN ('source_events','tracks')
                    AND r.namespace=NEW.namespace AND r.id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Immutable observation.'); END;
        CREATE TRIGGER platform_append_only_committed_asset_update
            BEFORE UPDATE ON platform_assets
            WHEN EXISTS(SELECT 1 FROM platform_source_packages
                WHERE session_id=OLD.session_id AND source_id=OLD.source_id)
            BEGIN SELECT RAISE(ABORT,'Immutable raw asset.'); END;
        CREATE TRIGGER platform_append_only_committed_asset_delete
            BEFORE DELETE ON platform_assets
            WHEN EXISTS(SELECT 1 FROM platform_source_packages
                WHERE session_id=OLD.session_id AND source_id=OLD.source_id)
            BEGIN SELECT RAISE(ABORT,'Immutable raw asset.'); END;
        CREATE TRIGGER platform_append_only_committed_asset_replace
            BEFORE INSERT ON platform_assets
            WHEN EXISTS(SELECT 1 FROM platform_assets a
                JOIN platform_source_packages p ON p.session_id=a.session_id
                WHERE a.id=NEW.id AND a.session_id=NEW.session_id)
            BEGIN SELECT RAISE(ABORT,'Immutable raw asset.'); END;
""",
    ),
    MigrationSpec(
        "platform.0011",
        "A",
        ("platform.0010",),
        """
        CREATE TABLE platform_artifact_staging(
            id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL,
            revision INTEGER NOT NULL, worker_id TEXT NOT NULL, scope_id TEXT NOT NULL,
            package_id TEXT NOT NULL UNIQUE, expires_ms INTEGER NOT NULL,
            spec TEXT NOT NULL, facts TEXT NOT NULL, accepted INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(session_id,run_id,revision)
                REFERENCES platform_runs(session_id,id,revision));
        CREATE TRIGGER platform_append_only_evidence_update BEFORE UPDATE ON platform_evidence
            BEGIN SELECT RAISE(ABORT,'Immutable evidence.'); END;
        CREATE TRIGGER platform_append_only_evidence_delete BEFORE DELETE ON platform_evidence
            BEGIN SELECT RAISE(ABORT,'Immutable evidence.'); END;
        CREATE TRIGGER platform_append_only_evidence_replace BEFORE INSERT ON platform_evidence
            WHEN EXISTS(SELECT 1 FROM platform_evidence
                WHERE namespace=NEW.namespace AND id=NEW.id)
            BEGIN SELECT RAISE(ABORT,'Immutable evidence.'); END;
    """,
    ),
    MigrationSpec(
        "platform.0012",
        "A",
        ("platform.0011",),
        """
        CREATE TABLE platform_run_state(
            id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, revision INTEGER NOT NULL,
            creator_id TEXT NOT NULL REFERENCES platform_accounts(id), credential_version
            INTEGER NOT NULL,
            as_of_ms INTEGER NOT NULL, input_hash TEXT NOT NULL, config_hash TEXT NOT NULL,
            config TEXT NOT NULL, payload TEXT NOT NULL, deadline_ms INTEGER NOT NULL,
            budget INTEGER NOT NULL CHECK(budget>=0), reserved INTEGER NOT NULL DEFAULT 0
            CHECK(reserved>=0),
            used INTEGER NOT NULL DEFAULT 0 CHECK(used>=0), version INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(session_id,id,revision) REFERENCES platform_runs(session_id,id,revision));
        CREATE TABLE platform_job_state(
            id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, run_id TEXT NOT NULL
            REFERENCES platform_run_state(id),
            stage TEXT NOT NULL, policy_hash TEXT NOT NULL, sources TEXT NOT NULL, assets TEXT
            NOT NULL,
            state TEXT NOT NULL, attempt_count INTEGER NOT NULL DEFAULT 0, ready_ms INTEGER NOT
            NULL,
            failure_code TEXT, FOREIGN KEY(session_id,id) REFERENCES platform_jobs(session_id,id));
        CREATE TABLE platform_attempt_state(
            id TEXT PRIMARY KEY NOT NULL, session_id TEXT NOT NULL, job_id TEXT NOT NULL
            REFERENCES platform_job_state(id),
            worker_id TEXT NOT NULL REFERENCES platform_workers(id), scope_id TEXT NOT NULL
            UNIQUE REFERENCES platform_worker_scopes(id),
            lease TEXT NOT NULL, state TEXT NOT NULL, reservation INTEGER NOT NULL
            CHECK(reservation>=0),
            charged INTEGER NOT NULL DEFAULT 0 CHECK(charged>=0), usage TEXT, failure_code TEXT,
            FOREIGN KEY(session_id,id) REFERENCES platform_attempts(session_id,id));
        CREATE TABLE platform_run_requests(
            actor_id TEXT NOT NULL, session_id TEXT NOT NULL, key TEXT NOT NULL, request_hash
            TEXT NOT NULL,
            run_id TEXT NOT NULL REFERENCES platform_run_state(id), payload TEXT NOT NULL,
            PRIMARY KEY(actor_id,session_id,key));
        CREATE TABLE platform_run_cancels(
            actor_id TEXT NOT NULL, run_id TEXT NOT NULL REFERENCES platform_run_state(id),
            key TEXT NOT NULL, expected_version INTEGER NOT NULL,
            PRIMARY KEY(actor_id,run_id,key));
        CREATE TRIGGER platform_append_only_run_cancels_update BEFORE UPDATE ON platform_run_cancels
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_run_cancels_delete BEFORE DELETE ON platform_run_cancels
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_run_cancels_replace
            BEFORE INSERT ON platform_run_cancels
            WHEN EXISTS(SELECT 1 FROM platform_run_cancels
                WHERE actor_id=NEW.actor_id AND run_id=NEW.run_id AND key=NEW.key)
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_job_receipts_update BEFORE UPDATE ON platform_receipts
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_job_receipts_delete BEFORE DELETE ON platform_receipts
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_job_receipts_replace BEFORE INSERT ON platform_receipts
            WHEN EXISTS(SELECT 1 FROM platform_receipts WHERE session_id=NEW.session_id AND
            attempt_id=NEW.attempt_id)
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_run_requests_update BEFORE UPDATE ON
            platform_run_requests
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_run_requests_delete BEFORE DELETE ON
            platform_run_requests
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        CREATE TRIGGER platform_append_only_run_requests_replace BEFORE INSERT ON
            platform_run_requests
            WHEN EXISTS(SELECT 1 FROM platform_run_requests WHERE actor_id=NEW.actor_id AND
            session_id=NEW.session_id AND key=NEW.key)
            BEGIN SELECT RAISE(ABORT,'Immutable receipt.'); END;
        """,
    ),
    MigrationSpec(
        "platform.0013",
        "A",
        ("platform.0012",),
        """
        CREATE TABLE platform_replay_snapshots(
            session_id TEXT NOT NULL, revision INTEGER NOT NULL,
            cache_key TEXT NOT NULL CHECK(length(cache_key)=64),
            checkpoint_ms INTEGER NOT NULL CHECK(checkpoint_ms>=0),
            reducer_version TEXT NOT NULL, payload TEXT NOT NULL,
            payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
            PRIMARY KEY(session_id,revision,cache_key,checkpoint_ms),
            FOREIGN KEY(session_id,revision) REFERENCES platform_revisions(session_id,revision));
        """,
    ),
)
