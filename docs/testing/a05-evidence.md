# A05 — Assets dan evidence acceptance

Tanggal: 9 Oktober 2026. A05.1–A05.2 done; Phase6.1 milik A done, shared Phase6 tetap in_progress karena jobs dan B. [Workflow](../development/private-assets-evidence.md).

Deliverables: assets/access.py, assets/routes.py, evidence/registry.py, optional artifact root/config/lifespan dan platform.0011. Source/contract1.0.0 dan dependency lock tetap. Prasyarat A03/A04 diperiksa sebelum implementasi; A04 phase docs diperbarui sebelum masuk A05.

9 acceptance cases `tests/platform/test_assets_evidence.py` menggunakan actual synthetic WAV, disposable SQLite/owner dan frozen fake transcript repository: authorized bytes/SHA/ranges/live revoke, event evidence scope/hash/exactquote, atomic registry rollback/commit/get, actual audio mapping/range/file presence, worker allowlist/cloud consent, HTTP range/no-store/private-path denial, verified/idempotent derivative + worker HTTP upload/incomplete/oversized/unauthenticated cleanup, unknown/future availability and transcript quote/backing anchors without raw grant. Missing file initially resolved incorrectly (RED), fixed by actual fd/hash verification; transcript malformed anchors regression also RED then fixed.

| Check | Result |
| --- | --- |
| Scoped assets/evidence suite | PASS9 |
| Full platform suite | PASS365 (356 previous +9) |
| Shared contract suites | PASS66 each A/B |
| Ruff check/format backend tests scripts | PASS60 files |
| mypy backend/flowlens | PASS42 files |
| Shared schema drift | PASS |
| Bandit -ll | PASS0 medium/high;2 existing low native subprocess findings, no suppressions |

No full-size throughput/capacity, real worker executable/provider, fidelity transform, real B/rule evidence adapters, private dataset/license, GOLD transcript/domain review, public network/TLS validation or maintenance purge. Startup pending TTL/orphan cleanup available; accepted artifact lifecycle remains A09. Durable bytes submitted are private pending, accepted result boundary comes A06. TestClient/thread/native decoder owners closed; no persistent process/container. G-BE/G-FE/G-DELIVERY not_started, HOST_ONLY readiness503.
