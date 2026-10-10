# Evidence local integration A/B

10 Oktober 2026. Input3917b1614be90e990419ab85edbef1d74e6bc155 pada feat/backend.
Candidate adalah commit pembawa [manifest](../development/backend-integration.json).
Environment macOS, Python3.12.14, FFmpeg/ffprobe9.0.2, SQLite lokal disposable,
locked dependencies (uv.lock unchanged). Real cloud calls0; no credentials supplied.

## Performed scope

`tests/platform/test_integration.py`:9 tests PASS. Actual API host lifecycle/fresh
23migration/FK catalog, A18-to-joint upgrade, guarded B repository inventory/purge,
development provider-disabled/production-blocked status, empty joint recovery;
normalized STT frozen JobResult → private intent/evidence/projection → B accepted
memory → B findings/brief → scoped human review/JSON/CSV/HTML export; immutable retry,
permission denial/revoke/idempotency conflict, unknown availability hidden AS_KNOWN;
nonempty backup/restore; exact B sensitive table purge; current tombstone applied to
old backup; bootstrap CLI against initialized joint ledger. Actual B executor uses
real FFmpeg with actual authenticated A HTTP routes and local rights despite cloud
rights denied. Forged provenance job rejected with zero promoted artifacts. Empty
brief result rejected before completion. Inputs synthetic, actual domain code B;
no provider quality or measured full capacity claim.

## Commands/results

All commands use root repository and `.venv`:

| Command | Result / limits |
| --- | --- |
| `python -m pytest tests/platform -q` | 729 PASS,1 opt-in capacity skip; final affected integration rerun9 PASS |
| `python -m pytest tests/analysis -q` |654 PASS |
| `python -m pytest tests/platform/test_integration.py -q` |9 PASS |
| `python -m flowlens.testing --track A` / `--track B` |66 PASS each; frozen1.0.0 |
| `python -m flowlens.testing.acceptance --output artifacts/reports/integration-b-acceptance.json` |9 local/MOCK commands PASS; real/account/benchmark fields remain pending |
| `ruff check backend tests scripts`; `ruff format --check backend tests scripts` |PASS,219 Python files formatted |
| `mypy` |148 source files PASS |
| `python -m flowlens.contracts.generate --check` |PASS; frozen DTO/ports/schema unchanged |
| `bandit -r backend/flowlens -ll` |No medium/high issues; excludes low findings |
| `pip-audit --local` |No known dependency vulnerabilities; unpublished project skipped |
| `uv lock --check`; `uv build --out-dir artifacts/reports/integration-dist` |PASS; unchanged lock |
| `PATH="$PWD/.venv/bin:$PATH" python scripts/package_smoke.py --wheel artifacts/reports/integration-dist/atc_flowlens-0.1.0-py3-none-any.whl --sdist artifacts/reports/integration-dist/atc_flowlens-0.1.0.tar.gz --output artifacts/reports/integration-installed.json` |PASS; disposable clean installed-wheel environment |
| `python scripts/checks/package_a_startup.py --expected-ready 200` |Native integrated development launcher health/release/OpenAPI200, local ready200, unauthenticated catalogue401; owned process/roots cleaned |
| `python scripts/checks/integration_worker_startup.py` |PASS; native API + separate B worker, authenticated HTTP IDLE; actual FFmpeg artifact flow tested via TestClient, not claimed native full-payload smoke |
| `python scripts/checks/integration_manifest.py` |Source/hash/23migration/62route catalog match |
| `python scripts/checks/scan_secrets.py --report artifacts/reports/integration-tracked-secrets.json` and `--staged` equivalent |Final counts below; known signatures only, no entropy/history certification |
| `git diff --check` |PASS |

Raw logs/builds/private disposable outputs are ignored under artifacts/reports/
integration-*. Earlier red logs retained separately; review/export fixture originally
had immutable export denied; fixture now explicitly grants original export permission
and tests current denial/revocation. Notice private field matched scoped A repository;
worker/API accepted-payload hash unified. A placeholder stage query was corrected to
actual platform_job_state; final reruns supersede initial failures. Requirements and
thresholds were not weakened. Local readiness changed because actual local AUDIO
coordinator now exists; provider and production gates did not change.

## Acceptance boundary

[Run guide](../development/backend-integration.md) identifies all remaining adapters,
workflows and limits. This evidence proves normalized local integration engineering,
not full Phase10/G-BE, raw SDK/provider smoke, canonical integrated S01–S12/held-out
quality or joint 60minute/100session/20object/two-channel capacity. A10 benchmark is
historical standalone A and preserved. Local source/build/tests/runtime available;
provider verified NO; domain NOT_DOMAIN_VALIDATED; operational validation NO.
Google/STT/Gemini key/profile and G-BE intentionally deferred. No frontend/container/
deploy, push, merge or amend performed by this local integration task.

Final recorded checks: platform729 PASS/1capacity opt-in skip; analysis654 PASS;
final affected integration+audio-worker83 PASS; Ruff219formatted/mypy148 PASS;
contracts66pertrack/schema/manifest/build/installed/native-API/native-worker PASS.
Manifest154 source/input hashes,23migrations,62operations. Signature scan483tracked
and36staged complete files,0findings. Bandit medium/high0,2low findings outside the
selected gate. Diff reviewed; historical migration SQL/frozen contracts/lock remain
byte-identical to input. Local candidate is the evidence-carrying commit; no push.
