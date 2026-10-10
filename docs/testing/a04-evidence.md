# Paket A04 — Import staging, metadata dan atomic publication

Tanggal: 9 Oktober 2026. A04.1–A04.2 sebelumnya341 platform PASS; unit A04.3 menyelesaikan managed raw promotion, session/source publication dan frozen SourceReader. A04/Phase3 done untuk canonical profiles; next A05. Tidak ada real B/provider integration, actual private data migration atau commit/push/deploy.

Deliverables: assets/storage.py, imports/commit.py, sources/{store,policy}.py, platform.0010, raw root host setting/lifespan dan bounded commit HTTP. Sources policy rechecked oleh permissions helper; source-owner rights versions audited. Prior A04.2 upgrade fixture dipin ke target0009 agar migration tambahan tidak mengubah arti assertions lama. A04.1/2 metadata dan stage tetap private/draft-only; current full envelope dibawa ke durable source registry.

15 cases tests/platform/test_import_commit.py: actual waveform copy/hash/read-only/private paths; no automatic grants; scoped stable receipt; identical dedup/different declaration conflict; mapped events/as-of filtering; unknown alignment tidak menciptakan rows; live source denial; raw manifest/observation/asset SQL mutation/replacement denial; callback faults at copy/promotion/precommit/postcommit; updated metadata during promotion denied; orphan recovery; authenticated HTTP commit/retry/CSRF/no-store/body cap/lifespan; actual subprocess os._exit at copy/promotion/after SQLite commit and restarted owner verifies package/DB/FKs.

| Check | Result |
| --- | --- |
| Initial commit test | RED: PrivateFiles/ImportCommit/Sources absent |
| HTTP setting/route test | RED: raw setting/commit unavailable |
| Immutable asset replacement regression | RED: UPDATE accepted; managed-package SQL guards added |
| Commit padded JSON cap regression | RED: oversized valid JSON accepted; streaming4KiB cap added |
| Full platform suite | PASS356 (341 prior +15 A04.3 cases) |
| Final changed commit/routing cases | PASS15 after body cap fix |
| Shared contracts A/B | PASS66 each |
| Ruff lint/format | PASS56 files |
| mypy | PASS39 source files |
| Shared schema drift | PASS |
| Bandit -ll | PASS0 medium/high;2 existing low subprocess findings, no suppressions |
| uv build artifacts/reports/a04-dist | PASS sdist/wheel |

Infrastructure evidence is synthetic/disposable. Independent source clock/unit oracles remain [A04.2](a042-evidence.md); raw waveform metadata fixture is not gold transcript or domain validation. No new STT/Gemini, geographic/corpus adapters, semantic source authenticity verification, real cloud rights/legal evidence, full-size capacity/performance, hardware power-loss or deployment validation. Retention read gate works; purge/backup maintenance is later A09. Source catalogue/replay controls remain A07. HOST_ONLY readiness503; all gates not_started. TestClient/DB owners/threads/native and crash subprocesses closed; ignored build artifacts remain. [Workflow](../development/import-commit.md).
