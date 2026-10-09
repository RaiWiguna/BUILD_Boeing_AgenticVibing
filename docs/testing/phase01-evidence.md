# Phase 0–1 completion evidence

Tanggal: 8 Oktober 2026 (Asia/Jakarta). Status: **done untuk Phase 0.1–0.4 dan 1.1–1.4**. Contract freeze: **1.0.0**. Parent commit: `fb1e1f7`; candidate berupa working tree tugas ini, belum commit/push. Source/business A/B dan G-BE belum selesai.

## Deliverables

| Subfase | Evidence |
| --- | --- |
| 0.1 | [FR-01–20/AC-01–20 audit dan source disposition](../product/requirement-audit.md) |
| 0.2 | [Offline/provider/P1 scope dan dependency register](../product/baseline-scope.md) |
| 0.3 | [Fixture/label/split protocol](../../evaluation/protocols/baseline.md), actual speech/silence WAV, manifest/events/layout, evaluator-only labels dan independent numeric/time oracle |
| 0.4 | [A/B packets](../development/backend-packets.md) dan [ownership/transactions](../architecture/backend-baseline.md) |
| 1.1 | Root pyproject/uv.lock, Python 3.12 virtualenv, install/build/lint/type/pytest entrypoints |
| 1.2 | Strict versioned Pydantic source/clock/quality/evidence/run/job/transcript/intent/association/memory/loop/finding/option/review/brief/query/snapshot/stream DTOs; valid/invalid examples |
| 1.3 | Protocol ports, safe error/status mapping, module registration, migration dependency ordering, standalone composition dan constrained reference UOW/SQLite |
| 1.4 | Both-track contract suite, MOCK adapters, real fixture inputs, generated public/internal schemas dan harness OpenAPI; [client generation strategy](../api/shared-contracts.md) |

## Performed checks

Environment: Python 3.12.14, macOS arm64, uv 0.12.23, disposable local SQLite. FastAPI 0.142.4, Pydantic 2.13.5; full resolved dependencies/hashes ada di uv.lock.

| Command/cakupan | Result | Evidence artifact |
| --- | --- | --- |
| `uv lock --check`, `uv sync --locked` | PASS; reproducible locked editable install | uv.lock + local .venv |
| `ruff check backend tests scripts` | PASS | terminal record; final checks |
| `ruff format --check backend tests scripts` | PASS | terminal record; final checks |
| `mypy` | PASS; 11 backend source files | terminal record; final checks |
| `pytest tests/contracts --track A -q` | PASS: 66 tests | artifacts/reports/phase01-track-a.txt |
| `pytest tests/contracts --track B -q` | PASS: 66 tests | artifacts/reports/phase01-track-b.txt |
| `python -m flowlens.testing --track A/B` | PASS; MOCK, provider_calls=0, disposable DB cleaned | CLI outputs / same subprocess assertions in tests |
| `python -m flowlens.contracts.generate --check` | PASS; no schema/OpenAPI drift | generated contracts/json-schema and contracts/openapi/baseline.json |
| `uv build` | PASS: source distribution and wheel | artifacts/reports/dist/ |
| Clean venv + hashed runtime requirements sync + wheel install without editable source/PYTHONPATH | PASS; A/B CLI and OpenAPI import | artifacts/reports/phase01-clean-install.txt |
| `bandit -r backend/flowlens -ll` | PASS; 0 issues at all severities | artifacts/reports/phase01-bandit.txt |
| `pip-audit --local` | PASS; no known dependency vulnerabilities | artifacts/reports/phase01-dependency-audit.txt |
| Documentation links/fences/tables, source secret-pattern scan, `git diff --check` | PASS on final documentation | artifacts/reports/phase01-document-checks.txt |

Tests cover unknown/future availability, scope/capability revocation, evidence hash/span/range, strict invalid enum/time/hash/nonfinite/extra command, UTC/null semantics, snapshot and typed stream mismatch, open-loop/query/artifact job envelopes, safe HTTP errors/status codes, production MOCK rejection, module callbacks, migration order/cycles/fresh/upgrade, scoped FK enforcement, local idempotency/restart, stale input/config/run/lease/deadline/budget/rights/cancel, rollback including evidence/audit, UOW callback publication after commit, isolated CLI and generated drift.

Test-first evidence (ignored local artifacts): phase01-red.txt (39 missing-contract failures), phase01-refinements-red.txt (5 gaps), phase01-handoff-red.txt (missing CLI), phase01-evidence-red.txt, phase01-job-red.txt, phase01-errors-red.txt dan phase01-output-types-red.txt. Bugs/cases were corrected before PASS; assertions were not removed to make tests pass.

## Immutable inputs for freeze

- contracts/models.py SHA-256: `aa034b0d72afc148f0a1456fa87a7c9a394c06d3c00c70f8c06f3fe68ab7ed5c`.
- uv.lock SHA-256: `7a9045918cd82355505ad3b0c9ddaf803c0b5fc2a0a7bc267225474617b4a8a6`.
- Audio source hashes, channel/rate/duration and clock mapping are recorded in fixtures manifest. No provider/model capability is inferred from these hashes.

## Limitations and gate impact

- Contract app is MOCK validation harness, `/ready` false/BASELINE_ONLY; business `/api/v1` routes, production auth/persistence/replay/detector/worker/AI are owner phases. Reference SQLite migrations are not historical archive migration.
- SDK adapters, FFmpeg/Shapely/auth dependencies and actual provider profiles are not implemented here. Real STT/Gemini access/model/API/features/region/quota/budget remain UNVERIFIED. No cloud calls/corpus transfer occurred.
- TTS waveform script is NOT_GOLD; pronunciation/time-span audit pending. Synthetic labels are NOT_DOMAIN_VALIDATED. No held-out benchmark, partner/domain/usability or operational validation is claimed.
- OpenAPI is baseline schema exchange; production OpenAPI/TS client freeze occurs at Phase 10. No React/npm frontend/container/Compose/VM work was started.
- pip-audit cannot audit unpublished atc-flowlens itself; its own source received lint/type/tests/Bandit checks. Secret-pattern scan is scoped local checking; dedicated Gitleaks/hosted CI/full security audit not run.
- Build/clean install proven on this Python/platform; no cross-platform support claim.
- Tests/CLIs used tempdirs and closed connections; no persistent server/worker/container remains. Only local .venv and ignored evidence/build artifacts remain.
- **G-BE/G-FE/G-DELIVERY: not_started.** Next: A Phase 2; B analysis module/repositories and Phase 6.2/6.4 independently. Integrate real packages only Phase 10.
