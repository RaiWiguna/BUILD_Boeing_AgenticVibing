# A09.3 — local consistent recovery

9 Oktober 2026, input clean `9f9ee3e442819d45c742a247db94810d1a0f1c1b`, branch feat/backend-aben. Real SQLite/private files/auth/jobs/evidence/replay; fake B melalui frozen ports. Tidak ada production data, cloud inference, deployment atau persistent daemon.

Source recovery/{maintenance,catalog,snapshots,candidates}.py, cli/maintenance.py dan migration0018 menyediakan offline exclusive maintenance, WAL-aware snapshot, manifest/hash/catalog verification, new isolated restore, current deletion/expiry reconciliation, active job/auth invalidation, bounded audit, immutable bundle retirement dan crash candidate cleanup. [Workflow dan limits](../development/recovery.md).

27 scoped tests PASS (12.16s) pada empat test_recovery modules: live owner/native CLI lock, fresh/17->18 upgrade/reopen, retained grants/revisions/transcript/evidence/export/checkpoint/cursor, active reservations/auth invalidation; committed WAL with native reader; tamper/traversal/symlink/current journal failure; newer purge/expiry before publication and fake frozen purge callback; copy ENOSPC, publication fsync rollback, audit pending; phase fault retries, partial retirement retry, actual subprocess os._exit crash and active candidate protection. Disk failure is fault-injected ENOSPC, not full physical-disk exhaustion.

Final712 platform PASS153.62s, contracts66 each A/B PASS, Ruff120/mypy78/drift/Bandit -ll/lock/build PASS. Scan/review details in the objective audit. Historical17 migration definitions remain AST-identical; only0018 appended. Frozen contracts1.0.0, schemas and dependency lock unchanged. No encrypted/off-host backup, runtime scheduler, real B/provider/domain/performance acceptance certification. A10.1 is next, not performed in this unit.

Final diff/source reviewed; staged21-file known-signature scan0 matches, dedicated scanners absent; links/fences/whitespace PASS. Local conventional commit only, no runtime/private fixtures staged.
