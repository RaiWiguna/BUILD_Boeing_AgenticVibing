# A04.1 — Private upload staging, validation dan preview

Tanggal: 9 Oktober 2026, Asia/Jakarta. Input cdb2b9d + uncommitted A03.1–A03.3. Rules/handoff/PRD dan package execution dibaca; prasyarat A03 lengkap diperiksa lewat source dan scoped mutations/transport129 tests PASS. Scope hanya A04.1; A04.2/A04.3 dan integrasi B tidak dikerjakan. A04.1/Phase3.1 done; A04/Phase3 in_progress; next A04.2.

## Deliverables dan acceptance

- imports/staging.py: private opaque draft files, streaming byte/SHA controls, explicit input profiles, owner/admin checks, quota/expiry, stable scoped key retries dan startup interrupted/expired/orphan recovery.
- imports/inspection.py: complete WAV/FLAC decode di subprocess fd, duration/channels/sample/metadata bounds; strict canonical events/tracks JSON/JSONL/CSV dan safe row failures. No normalization/provider input.
- imports/routes.py: custom streaming multipart POST `/api/v1/imports`, owner-only GET preview, raw filename traversal guard, bounded headers/body/timeout, inherited cookie/Origin/CSRF/no-store policy.
- Host optional FLOWLENS_IMPORT_STAGING_PATH/lifespan/safe errors, additive platform.0008. Earlier A03.3 migration fixture dipin ke sebelum0007 agar penambahan0008 tidak mengubah arti upgrade test. Prior assertions dipertahankan.
- Preview metadata/remediation: channels/rate/frames/duration/hash/size/counts, tracks presence, unknown clock/layout, undeclared rights blocking; no storage path/key/raw content/truth. Accepted raw bytes tetap original, tidak ada replay sessions/source/assets/jobs/runs committed.
- pyproject/uv.lock menambah soundfile0.14.0 dan python-multipart0.0.32; observed libsndfile1.2.2, numpy2.5.3 transitive. Shared contracts/ports/generated baseline1.0.0 unchanged; committed platform0001–0005 checksums unchanged, prior0006/0007 retained.

35 cases di tests/platform/test_imports.py: real synthetic WAV/FLAC, known fixture8021ms/128343frames, float NaN/Inf, invalid/truncated containers, byte/duration/channel/hash limits,6 unsafe filename forms dan Windows multipart path, strict sidecar JSON nonfinite/duplicate/truth, JSONL/explicit unit CSV, raw bytes preservation, absence of domain rows, owner/credential revocation, tamper/symlink refusal, HTTP201/422/403/409 no-store, same-key retry at quota, changed payload conflict, broken iterator/unsealed/incomplete multipart cleanup, decoder timeout fault, sanitized child environment, root safety, interrupted/orphan/restart preservation dan expired cleanup. Timeout branch memakai fault injection; native normal decode benar-benar dijalankan, tidak memerlukan provider.

## Checks

Python3.12.14/macOS arm64; real SQLite/Argon2/TestClient/native decoder dengan disposable DB/private dirs dan synthetic principals. Belum menjalankan live network upload atau provider smoke.

| Check | Result |
| --- | --- |
| Windows multipart traversal regression | RED: compatibility parser strips path; raw header checked before parsing, assertion retained |
| Preview completeness regression | RED: unknown fields absent; explicit unknown/presence fields added |
| Expired receipt retry regression | RED: POST identical key returned expired draft; finalization checks original expiry, assertion retained |
| Decoder environment regression | RED: host env inherited; minimal explicit environment added |
| macOS decoder memory rlimit diagnosis | Runtime rejected RLIMIT_AS/DATA/RSS; CPU/wall/bounded decode works; no hard memory claim on Darwin |
| `.venv/bin/python -m pytest tests/platform -q` | PASS,312 (277 prior +35 import cases) |
| `.venv/bin/python -m pytest tests/contracts --track A -q` | PASS,66 |
| `.venv/bin/python -m pytest tests/contracts --track B -q` | PASS,66 |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format --check backend tests scripts` | PASS,46 files |
| `.venv/bin/mypy` | PASS,31 source files |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS threshold:0 medium/high;2 low B404/B603 subprocess import/call, fixed argv/pass_fds/no shell; no skips/suppressions |
| `.venv/bin/pip-audit --local` | PASS,no known Python dependency vulnerabilities; unpublished local app skipped |
| `.venv/bin/uv build --out-dir artifacts/reports/a041-dist` | PASS,sdist/wheel |
| Committed migration checksum AST/HEAD comparison | PASS,platform0001–0005 unchanged |
| Changed Markdown links/fences/whitespace + `git diff --check` | PASS,19 changed Markdown files |

## Limits dan cleanup

Input format/resource/runtime scope terinci pada [workflow](../development/import-preview.md) dan [ADR](../adr/0003-private-import-staging.md). Canonical validation bukan identity/time/rights normalization, paired conformance eligibility atau manifest completeness. Full resource maxima/throughput dan Linux memory cap belum diuji; macOS decoder bukan sandbox/hard-memory isolated. Python dependency audit tidak membuktikan native libsndfile CVE coverage. Initial engineering quotas bukan VM capacity claim; expired draft reclaim startup-only.

FS draft cleanup/restart diperiksa, tetapi atomic DB+FS source promotion/power-loss fault boundaries tetap A04.3. No actual rights declaration, committed-source reader, media endpoint, STT, Gemini atau real B. Test fixture script/label bukan automatic gold transcript/domain validation. Gate G-BE/G-FE/G-DELIVERY tetap not_started; readiness503/HOST_ONLY.

Disposable owners/connections/TestClient dan native subprocess selesai; a041-dist ignored tersedia. No persistent server/worker/container, real account/data migration, provider call, commit/push/merge/deploy. Next A04.2 manifest/rights/retention/coverage dan explicit clock/timezone/identity/units/layout normalization.
