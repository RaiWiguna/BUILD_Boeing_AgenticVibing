# A03.2 — HTTP/WS policy dan public serializers

Tanggal: 9 Oktober 2026, Asia/Jakarta. Input HEAD cdb2b9d + A03.1 working tree yang belum commit/push. Prasyarat diverifikasi dari source, grants/state/schema/guard dan 60 tests permissions+sessions PASS. A03.2 done; A03/Phase 2 in_progress, Phase 2.3 done, next A03.3/Phase 2.4. Contract1.0.0, platform.0001–.0006 dan lock unchanged.

## Deliverables dan acceptance

- auth/transport.py: host HTTP guard, exact Origin/CSRF/cookie policy, separate worker bearer principal, scoped HTTP/worker helpers dan WS pre-accept/recheck policy. Permissions.authenticate_worker memverifikasi hashed credential expiry/revocation tanpa memberi domain scope.
- api/serializers.py: live-UOW authorization, exact typed observed DTO allowlist, nested scope/revision/time/mode checks, canonical revalidation dan source/asset projection sesuai capabilities.
- host HTTP integration/no-store dan safe WS validation/contract/HTTP/unexpected error handling; auth helpers memakai shared HTTPConnection. tests/platform/test_transport.py: 71 cases, real disposable SQLite/Argon2 dan synthetic principals, injected test module via frozen ModuleRegistration.
- Existing error/validation tests memakai authenticated disposable setup agar tetap mencapai safe handlers. Login input test memakai valid Origin. Legacy routes tetap absent; legacy bearer kini 403 sebelum routing. Cookie-only test memeriksa explicit bearer/query rejection 403. Tidak menghapus private-error assertions atau menonaktifkan guard agar tests lulus.

Coverage: POST/PUT/PATCH/DELETE CSRF/origin/cross-site no-effect denial; safe read exact/absent Origin policy; duplicate security headers/cookies; query/context claims; live logout/reset/forced-change/expiry; cross-session/run/capability; server-built clock/mode; human/worker separation, browser metadata denial, cross-worker scope/expiry/revoke; WS before-accept denial dan recheck setelah grant revoke/logout/reset/expiry; safe WS validation/HTTP/contract/unexpected errors; public manifest without audio inventory, authorized asset metadata tanpa fixture/private path; raw/internal/truth/private/subclass denial, forged/revoked/worker contexts; nested snapshot revision/mode, future/unknown availability, invalid model_copy dan input immutability.

## Performed checks

Python 3.12.14/macOS arm64. Tests menggunakan TestClient dan disposable DB, tanpa runtime/data akun pengguna atau inference cloud.

| Check | Result |
| --- | --- |
| Initial generic guard/CSRF/origin tests sebelum implementation | RED: uncredentialed/invalid mutation routes mengembalikan 200; 24 negative cases reproduced |
| Initial public serializer test | RED: public projection module belum tersedia |
| WS validation reason regression | RED: FastAPI default mengembalikan input private-password dalam close reason; assertion dipertahankan, handler diperbaiki |
| WS HTTP/unexpected exception regression | RED: existing HTTP handler tidak dapat menangani socket; unexpected exception keluar; safe handlers/boundary diperbaiki |
| `.venv/bin/pytest tests/platform -q` | PASS, 219 (148 prior + 71 A03.2) |
| `.venv/bin/pytest tests/contracts --track A -q` | PASS, 66 |
| `.venv/bin/pytest tests/contracts --track B -q` | PASS, 66 |
| `.venv/bin/ruff check backend tests scripts` | PASS |
| `.venv/bin/ruff format --check backend tests scripts` | PASS, 40 files |
| `.venv/bin/mypy` | PASS, 27 source files |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| `.venv/bin/uv build --out-dir artifacts/reports/a032-dist` | PASS, sdist/wheel |
| Changed documentation links/fences dan `git diff --check` | PASS |

## Limits dan cleanup

No new domain/admin/worker job/media/export route. HTTP/WS scope guards dan serializers harus dipakai oleh future handler dengan server-selected capability/classification; host principal guard saja tidak membuktikan object access. Tidak ada evaluator truth public schema; explicit truth route contract masih perlu dirancang saat owner membangun reader. Source text/private schedule classification tetap trusted reader responsibility, bukan heuristic scrubbing.

Policy WS diuji lewat TestClient probe, termasuk recheck setelah invalidation; real replay connection/publication scheduling/disconnect/resync tetap A07.3. Actual media/export rights/range tetap A05/A09, worker lease/coordinator A06, internal proxy network denial/TLS VM Phase15. Tidak ada live network WS smoke, provider calls, real B, domain benchmark atau operational validation. Readiness503/HOST_ONLY dan G-BE/G-FE/G-DELIVERY tetap not_started.

Disposable TestClient/SQLite owners ditutup. Ignored build artifacts artifacts/reports/a032-dist tersedia. Tidak ada persistent server/worker/container, real account/data migration, commit/push/merge/deploy. [Workflow](../development/transport-policy.md). Next A03.3; jangan lanjut otomatis ke A04 atau integrasi B.
