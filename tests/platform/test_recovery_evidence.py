"""Real evidence/transcript lineage survives isolated restore; old proofs do not."""

import importlib

from flowlens.evidence.registry import EvidenceRegistry
from pydantic import SecretStr
from test_assets_evidence import media as media
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_jobs import active, candidate
from test_recovery import paths, service, stop_fixture


def test_evidence_and_transcript_versions_preserved_and_resolvable(
    media, committed, importer, tmp_path
):
    jobs, run, worker, client, lease = active(media, committed, importer)
    value = candidate(media, jobs, worker, lease)
    client.result(value)
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        receipt = cls(m).create(tmp_path / "backup")
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=receipt.manifest_hash,
        clock=lambda: now[0],
    )
    with service(restored.paths, now) as m:
        auth = m.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        context = m.permissions.human_context(
            auth.token.get_secret_value(), media[2].session_id, run_id=run.id
        )
        assert (
            EvidenceRegistry(m.sources, m.assets).resolve(context, value.evidence[0])
            == value.evidence[0]
        )
        with m.database.begin() as uow:
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_evidence").fetchone()[0] == 1
            )
            transcript = uow.connection.execute(
                "SELECT payload FROM platform_records WHERE namespace='analysis.transcripts'"
            ).fetchone()[0]
            assert "Synthetic phrase" in transcript
            assert uow.connection.execute(
                "SELECT input_hash,config_hash FROM platform_run_state WHERE id=?", (str(run.id),)
            ).fetchone()[:] == (lease.input_hash, lease.config_hash)
