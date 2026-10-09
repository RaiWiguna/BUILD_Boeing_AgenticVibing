# A02.2 — Login/logout, opaque cookie sessions, expiry dan rate limits

Tanggal: 9 Oktober 2026, Asia/Jakarta. A02.2/A02/Phase 2.2 **done**; Phase 2 masih in_progress (2.3–2.4 planned). Input c36cf04 + uncommitted A02.1; candidate working tree, belum commit/push. Contract 1.0.0 dan dependency lock dari A02.1 tidak berubah oleh A02.2.

Deliverables: `auth/sessions.py`, `auth/routes.py`, platform.0005, host/router/service lifecycle, origin config, forwarding-disabled launcher, successful Argon2 rehash/credential race guard, `tests/platform/test_sessions.py`, affected regression assertions dan [auth guide](../development/authentication.md).

## Performed checks

Python 3.12.14/macOS arm64, real Argon2/SQLite/temp DB; HTTP transport via TestClient serta actual loopback subprocess.

| Check | Result |
| --- | --- |
| Initial session suite before implementation | 12 missing-feature failures |
| Proxy-header guard / password-change rate budget before fixes | RED regressions reproduced; assertions preserved |
| `.venv/bin/pytest tests/platform -q` | 110 PASS (88 prior + 22 session/config/HTTP cases) |
| Shared contract suite track A / B | 66 PASS masing-masing |
| `.venv/bin/python -m flowlens.contracts.generate --check` | PASS |
| Ruff check/format backend/tests/scripts | PASS, 35 files format |
| `.venv/bin/mypy` | PASS, 24 source files |
| `.venv/bin/bandit -r backend/flowlens -ll` | PASS, 0 issues |
| `.venv/bin/uv build --out-dir artifacts/reports/a022-dist` | PASS, sdist/wheel |
| Actual loopback HTTP login/session/CSRF logout/replay old cookie | PASS; revoked access 401, HttpOnly, no raw token in JSON |
| Actual forwarded-header smoke | PASS; rate key actual 127.0.0.1 despite supplied X-Forwarded-For |
| Scoped secret patterns / documentation links/fences / git diff --check | PASS |

Account host test yang sebelumnya berharap missing login route kini mengharapkan 422 untuk empty body pada implemented endpoint. Host launcher test menambahkan proxy_headers=false assertion. Old operator/token routes tetap absent. Baseline schema generation tetap memakai separate harness dan tidak direlabel sebagai production API freeze.

Coverage: persistent hashed sessions; HTTP/HTTPS cookie attributes, same-origin and CSRF denials, malformed/wrong/unknown login, no bearer/query fallback, token rotation/logout, idle/exact absolute expiry/restart, failed commit without cookie, durable account/peer throttling before hashes, two-slot crypto bound, password-change attempt budget, forced-change flow, reset/deactivation invalidation, rehash and safe public views. Test secret/cookie values synthetic dan disposable.

## Limits / handoff

- CSRF/Origin guards pada auth mutations saja, sebagai prerequisite keamanan endpoint baru. Generic HTTP/WS/media/internal policy tetap A03/A07; belum ada domain grants atau server-built replay RequestContext.
- No TLS VM/browser journey/WS disconnect/performance benchmark/full load/security audit. Configured HTTPS TestClient check membuktikan Secure cookie metadata saja.
- Fixed-window limits adalah baseline; raw IP berasal dari supported launcher yang tidak mempercayai forwarding. Trusted Caddy proxy/release topology menunggu Phase 15.
- Self-service recovery/email/MFA dan HTTP admin management tidak ditambahkan; reset/deactivation tersedia via trusted account service A02.1. Sessions/status/password-change/logout limited to authenticated cookie context.
- Dependency audit A02.1 tetap record terpisah (lock tidak berubah); clean wheel install/hosted CI tidak dijalankan di unit ini. Gitleaks unavailable, scoped patterns bukan full secret audit.
- Real smoke membuat temp synthetic admin/DB saja; subprocess dihentikan dan tempdir dihapus. Build artifacts ignored di a022-dist tersedia; tidak ada persistent runtime, provider calls, commit/push/merge/deploy.
- Next A03.1: grants/capabilities, trusted server-built RequestContext dan worker principal. Semua gates tetap not_started.
