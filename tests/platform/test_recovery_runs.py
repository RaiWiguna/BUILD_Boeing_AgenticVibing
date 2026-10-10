"""Restore real grants/revisions/evidence/jobs/checkpoints/export with frozen fake B."""

import importlib

import pytest
from flowlens.core.errors import ContractError
from flowlens.jobs.coordinator import StageInput
from flowlens.replay.controls import Controls
from flowlens.replay.snapshots import Replay
from test_import_commit import committed as committed
from test_imports import importer as importer
from test_recovery import paths, service, stop_fixture
from test_report_artifacts import exporting, result, spec
from test_report_artifacts import media as media


def test_restore_completed_export_and_checkpoint_but_cancels_active_delivery(
    media, committed, importer, tmp_path
):
    jobs, run, client, lease, wc = exporting(media, committed, importer)
    artifact = spec(wc)
    body = b'{"label":"SYNTHETIC"}'
    media[0].submit(wc, artifact, iter([body]))
    client.result(result(lease, artifact))
    old_token = committed[3].token.get_secret_value()
    controls = Controls(Replay(committed[1]))
    controls.command(
        old_token,
        media[2].session_id,
        "SEEK",
        view="LOCAL",
        value=1000,
        key="cursor",
        expected_version=0,
    )
    replay_context = controls.context(old_token, media[2].session_id, view="LOCAL")
    controls.replay.snapshot(replay_context)
    policy = jobs.policies["EXPORT"]
    pending = jobs.create(
        media[2],
        policy.config,
        [StageInput(stage="EXPORT", source_ids=[media[3].source_id], asset_ids=[])],
        budget=300,
        deadline_ms=50000,
        expected_revision=media[2].input_revision,
        key="pending",
    )
    active = client.lease(lease.owner_id, "EXPORT")
    assert active is not None
    p = paths(media, importer, tmp_path)
    now = importer[2]
    stop_fixture(media, importer)
    cls = importlib.import_module("flowlens.recovery.snapshots").Snapshots
    with service(p, now) as m:
        created = cls(m).create(tmp_path / "backup")
        before = m.check()
        assert before["checkpoints"] > 0
    restored = cls.restore(
        tmp_path / "backup",
        tmp_path / "restored",
        journal_path=p.journal,
        expected_manifest_hash=created.manifest_hash,
        clock=lambda: now[0],
    )
    with service(restored.paths, now) as m:
        assert m.check() == before
        with pytest.raises(ContractError):
            m.sessions.resolve(old_token)
        with pytest.raises(ContractError):
            m.sources.read_events(replay_context)
        with m.database.begin() as uow:
            assert (
                uow.connection.execute(
                    "SELECT state FROM platform_attempt_state WHERE id=?", (str(active.attempt_id),)
                ).fetchone()[0]
                == "CANCELLED"
            )
            assert uow.connection.execute(
                "SELECT reserved,used FROM platform_run_state WHERE id=?", (str(pending.id),)
            ).fetchone()[:] == (0, active.budget_microunits)
            assert (
                uow.connection.execute("SELECT COUNT(*) FROM platform_context_receipts").fetchone()[
                    0
                ]
                == 0
            )
        from pydantic import SecretStr

        auth = m.sessions.login("admin", SecretStr("synthetic-import-changed"), "local")
        token = auth.token.get_secret_value()
        context = m.permissions.human_context(token, media[2].session_id, run_id=run.id)
        lifecycle = importlib.import_module("flowlens.artifacts.lifecycle").Artifacts(m.assets)
        assert b"".join(lifecycle.download(context, artifact.id)) == body
        cursor = m.controls.context(token, media[2].session_id, view="LOCAL")
        assert cursor.as_of_ms == 1000
