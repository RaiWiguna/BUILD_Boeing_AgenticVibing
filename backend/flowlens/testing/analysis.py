"""B01 standalone MOCK platform; disposable SQLite only, never host composition.

Platform reference keys mirror platform.0001, without importing Package A.
Evidence/audit/event UOW primitives reuse the frozen shared reference harness.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from flowlens.analysis.config import AnalysisConfig
from flowlens.analysis.module import AnalysisFoundation, register_analysis
from flowlens.analysis.repository import NAMESPACE, SQLiteConfigurationRepository
from flowlens.analysis.schema import ANALYSIS_MIGRATIONS
from flowlens.contracts.models import RequestContext
from flowlens.contracts.ports import Repository
from flowlens.core.modules import MigrationSpec, ModuleRegistry, order_migrations
from flowlens.testing.harness import SQLiteTransactionFactory, SQLiteUnitOfWork

PLATFORM_REFERENCE = MigrationSpec(
    "platform.0001",
    "A",
    (),
    """
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
    """,
)


class AnalysisReferenceUOW(SQLiteUnitOfWork):
    def repository(self, namespace: str) -> Repository:
        self.check_open()
        if namespace == NAMESPACE:
            return SQLiteConfigurationRepository(self.conn, self.check_open)
        return super().repository(namespace)


class AnalysisReferenceTransactions(SQLiteTransactionFactory):
    """Explicit MOCK adapter; construction does not create authorized parent data."""

    def __init__(self, path: Path, *, install_analysis: bool = True) -> None:
        super().__init__(path)
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS mock_migrations(id TEXT PRIMARY KEY, hash TEXT)"
            )
            conn.commit()
        self.migrate(
            (PLATFORM_REFERENCE, *ANALYSIS_MIGRATIONS)
            if install_analysis
            else (PLATFORM_REFERENCE,)
        )

    def migrate(self, manifest: Sequence[MigrationSpec]) -> None:
        ordered = order_migrations(list(manifest))
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                applied = dict(conn.execute("SELECT id, hash FROM mock_migrations"))
                if set(applied) - {item.id for item in ordered}:
                    raise ValueError("MOCK manifest downgrade forbidden")
                for item in ordered:
                    digest = hashlib.sha256(
                        repr((item.id, item.owner, item.depends_on, item.sql)).encode()
                    ).hexdigest()
                    if item.id in applied:
                        if applied[item.id] != digest:
                            raise ValueError("MOCK applied migration changed")
                        continue
                    # B01 manifests contain simple CREATE statements. No executescript commit.
                    for statement in item.sql.split(";"):
                        if statement.strip():
                            conn.execute(statement)
                    conn.execute("INSERT INTO mock_migrations VALUES (?,?)", (item.id, digest))

    def seed(self, context: RequestContext) -> None:
        """Test-only platform setup, distinct from B domain writes."""
        if context.analysis_run_id is None:
            raise ValueError("Run required")
        with self.begin() as uow:
            conn = uow.conn
            conn.execute(
                "INSERT OR IGNORE INTO reference_sessions VALUES (?)", (str(context.session_id),)
            )
            conn.execute(
                "INSERT OR IGNORE INTO platform_sessions VALUES (?)", (str(context.session_id),)
            )
            conn.execute(
                "INSERT OR IGNORE INTO platform_revisions VALUES (?,?,?)",
                (str(context.session_id), context.input_revision, context.input_hash),
            )
            conn.execute(
                "INSERT INTO platform_runs VALUES (?,?,?)",
                (str(context.session_id), str(context.analysis_run_id), context.input_revision),
            )
            uow.commit()

    @contextmanager
    def begin(self) -> Iterator[AnalysisReferenceUOW]:
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            uow = AnalysisReferenceUOW(conn)
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield uow
            except BaseException:
                uow.rollback()
                raise
            finally:
                if not uow.committed:
                    uow.rollback()
        if uow.committed:
            for callback in uow.callbacks:
                callback()


def main() -> None:
    context = RequestContext(
        actor_id=UUID(int=3),
        capabilities=["read", "analysis", "admin"],
        session_id=UUID(int=1),
        analysis_run_id=UUID(int=2),
        input_revision=1,
        input_hash="a" * 64,
        as_of_ms=0,
        mode="AS_KNOWN",
        request_id=UUID(int=4),
    )
    with TemporaryDirectory(prefix="flowlens-b01-") as temp:
        transactions = AnalysisReferenceTransactions(Path(temp) / "b01.db")
        transactions.seed(context)
        registration = register_analysis(AnalysisConfig(profile="test"), transactions)
        registry = ModuleRegistry(profile="test")
        registry.register(registration)
        service = registration.services["analysis"]
        if not isinstance(service, AnalysisFoundation):
            raise RuntimeError("Foundation service missing")
        with transactions.begin() as uow:
            service.configure(context, uow)
            uow.commit()
        if len(service.inventory(context)) != 1 or service.ready():
            raise RuntimeError("Foundation invariant failed")
        with transactions.begin() as uow:
            service.purge(context, uow)
            uow.commit()
        if service.inventory(context):
            raise RuntimeError("Purge failed")
    print(
        json.dumps(
            {
                "profile": "MOCK",
                "track": "B",
                "unit": "B01",
                "contract_version": "1.0.0",
                "provider_calls": 0,
                "pipeline_ready": False,
                "status": "passed",
                "database": "disposable-cleaned",
            }
        )
    )


if __name__ == "__main__":
    main()
