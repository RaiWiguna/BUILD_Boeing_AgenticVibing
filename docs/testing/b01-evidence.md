# B01 — analysis foundation evidence

Tanggal: 9 Oktober 2026. Branch `feat/backend-rai`; input/candidate base SHA
`cdb2b9dae3d16c22a524b8a05b2e5583cc48e0d0` + uncommitted B01 working tree.
Tidak ada commit/push/merge. Contract `1.0.0`; analysis migration `analysis.0001`,
dependency `platform.0001`; local config version `b01-1`.

## Implementasi dan manifest

- `backend/flowlens/analysis/{config,schema,repository,module}.py`, entrypoint
  `flowlens.analysis:register_analysis`: strict immutable config/run binding,
  SHA-256 config hash, API-side foundation service, injected repository factory.
- `analysis_configurations`: scoped run/revision FKs, positive revision, JSON/hash
  constraints, UUID key and unique session/run/revision. No automatic parent create.
  Input hash checked against context and platform revision within the same UOW.
- Namespace `analysis.configuration`; config append/audit/internal ledger event
  share caller UOW. No implicit commit/provider call; inventory uses transaction port.
  Admin purge exact session/run/revision, table B only. Platform ledger/audit retention
  remains A; config ledger metadata contains no transcript/credential/provider payload.
- Routes/job handlers/snapshot reader absent. validate/accept/snapshot explicitly
  NOT_EVALUABLE. Readiness false; inventory is configuration only. No accepted-result
  coordinator/receipt implementation in B01. No real A/B composition before Phase 10.
- Config keys: schema_version/profile/config_version/pipeline_enabled; pipeline_enabled
  only false. Registration propagates MOCK transaction marker; production rejects MOCK.
- `backend/flowlens/testing/analysis.py`: disposable MOCK platform reference schema
  matching platform.0001 parent keys, shared reference evidence/audit/event UOW,
  atomic test migration ledger/order/upgrade/checksum rejection. Test runner is not A's
  production migration engine; simple B01 SQL only. Repository runtime imports only
  B/shared contracts/core, standard library and Pydantic; no evaluator labels/oracles.
- Shared harness fix: constructor now closes SQLite connection explicitly (SQLite
  context manager alone only finishes a transaction), plus UOW repository return
  annotation widened to existing Repository port for B factory specialization.
  Frozen models/ports/schema outputs/pyproject/uv.lock unchanged.

## Environment dan commands

Windows x86_64 / PowerShell, CPython 3.12.15, SQLite 3.53.1, uv 0.12.23,
FastAPI 0.142.4, Pydantic 2.13.5; other versions/hashes follow uv.lock.
Host initially only exposed Python 3.13. `python -m pip install uv==0.12.23`,
then uv downloaded 3.12.15. Managed minor-version link detection failed; using the
explicit downloaded python.exe path with `python -m uv sync --locked --python
C:\Users\ASUS\AppData\Roaming\uv\python\cpython-3.12.15-windows-x86_64-none\python.exe`
successfully installed the unchanged lock into ignored `.venv`.

Below commands run from workspace; tools resolve from `.venv\Scripts\`.

| Command | Actual result |
| --- | --- |
| `python -m pytest tests/contracts --track B -q` before source edits | 64 passed / 2 failed: both standalone CLI cleanup cases WinError32 from leaked constructor connection |
| `python -m pytest tests/analysis -q` | PASS: 21 tests |
| `python -m pytest tests/contracts --track B -q` after fix | PASS: 66 tests |
| `python -m pytest tests/contracts --track A -q` | PASS: 66 tests |
| `python -m flowlens.testing --track B` | PASS: MOCK, provider_calls=0, disposable-cleaned |
| `python -m flowlens.testing.analysis` | PASS: B01/MOCK, pipeline_ready=false, provider_calls=0, disposable-cleaned |
| `ruff check backend tests scripts` | PASS |
| `ruff format --check backend tests scripts` | PASS |
| `mypy backend/flowlens/analysis backend/flowlens/testing/analysis.py` | PASS: 6 source files, native Windows |
| `mypy --platform linux` | PASS: 30 backend source files, baseline POSIX target |
| `mypy` | FAIL: 7 existing Windows incompatibilities in A database.py/bootstrap_admin.py (O_NOFOLLOW/flock/LOCK_EX/LOCK_NB/geteuid); zero B errors |
| `python -m flowlens.contracts.generate --check` | PASS: no frozen schema/OpenAPI drift |
| `bandit -r backend/flowlens -ll` | PASS: zero issues across all severities |
| `pip-audit --local` | PASS: no known dependency vulnerabilities; unpublished atc-flowlens itself skipped |
| `python -m uv build --out-dir artifacts/reports/b01-dist` (host Python invokes uv) | PASS: sdist + wheel |
| `git diff --check` | PASS |

## Acceptance coverage

Fresh installation and upgrade from reference platform-only DB preserve parent IDs;
dependency order, missing dependency, changed migration/downgrade and failed batch
rollback tested. FK remains enabled and FK check is clean; missing/cross-run parent,
revision and hash constraints reject writes. Scoped read/append/inventory/purge,
permission denial, config revalidation, duplicate immutable binding conflict and
closed repository guard tested. Domain/evidence/audit/event all disappear on rollback;
audit/event injected failures and omitted commit leave zero partial data. Publication
callback observes durable data through a new transaction; callback failure preserves
committed data, restart reconstructs identical inventory. MOCK production denial,
unsupported pipeline rejection and AST import allowlist enforce initial boundary.

Result acceptance/idempotency remains B02–B05/coordinator A06 scope. Existing shared
reference suite tests receipts/late results, but B01 claims no real accepted pipeline.
Local config record is internal persistence/ledger metadata, not a new public wire
contract or browser StreamEvent. Snapshot/resync integration remains Phase 10.

## Limitations dan next unit

B01 foundation acceptance passes on disposable SQLite. Whole-backend native Windows
typecheck does not pass because Package A is POSIX-only; B scoped Windows and full
POSIX-target static checks pass. No Package A portability change or real host run
claimed. No clean-wheel-install smoke beyond build in this unit.

No provider/FFmpeg worker/transcript/correction/association/memory/finding/review/export
pipeline, provider smoke, pronunciation gold audit, benchmark, domain review or
operational validation. No cloud calls or real data processing. Existing synthetic
fixtures/waveforms and evaluator truth were not regenerated/loaded into runtime.
Real Google STT V2/Gemini target access/transport/SDK/model/region/quota/budget are
external dependencies for B03/B04; no provider replacement.

Paket B remains in_progress; B02–B06 planned. Phase 7.3 still incomplete; parent
Phase 6/9 and G-BE/G-FE/G-DELIVERY remain open/not_started. Next B02.1 / Phase 6.2:
controlled FFmpeg decode/resample/chunk and channel/source time/gap/overlap tests.
Then B02.2 / Phase 6.4 isolated worker through JobClient/AssetAccess.

All tests use disposable DB/tempdirs and terminate subprocess CLIs. No server,
worker, container or daemon started. Ignored .venv/toolchain and b01-dist build
artifacts remain; original untracked docs/pitch, tests/browser and tmp preserved.
Final passing CLI tests cleaned their tempdirs. The two initial failed-baseline
tempdirs `flowlens-contract-svjirusb` and `flowlens-contract-5bjy4z19` under the
user's local Temp remain: automatic approval review rejected the explicitly scoped
PowerShell cleanup with "blocked by policy". No bypass or further deletion attempted.
