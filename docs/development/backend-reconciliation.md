# Reconciliation source Paket A dan B

10 Oktober 2026, branch `feat/backend-aben`. Dokumen ini mencatat resolution konflik untuk PR menuju `feat/backend`; belum menutup integrasi runtime Phase 10.

## Input dan keputusan resolution

- Paket A: `0be155589f2362b354fe8463a041f43b67cc6267`, termasuk A10.1 `eb5205b33cab76b991eea08ca671acd4431c83b3` dan A10.2.
- Target Paket B: `736659190706847129d123bd442a3ea720e6ddbd` dari `origin/feat/backend`.
- Merge base: `cdb2b9dae3d16c22a524b8a05b2e5583cc48e0d0`.
- Resolution commit: `git log -1 --format=%H -- docs/development/backend-reconciliation.json`. Commit mempunyai kedua input sebagai parent; target branch tidak diperbarui oleh pekerjaan ini.

Tujuh file dengan 19 conflict blocks adalah `.agent/implementationPhases.md`, `.agent/sessionHandoff.md`, `docs/README.md`, `docs/architecture/repository-structure.md`, `docs/development/backend-packets.md`, `pyproject.toml`, dan `uv.lock`. Status A dan B dipadukan, historical handoff/evidence dipertahankan, dan dependency union menyertakan `types-shapely` serta `types-protobuf`. Lock diregenerate dengan uv: 87 package, tanpa perubahan versi package yang sudah terdapat pada salah satu parent. Runtime SDK B tetap `google-cloud-speech==2.41.0` dan `google-genai==2.29.0`; FastAPI A tetap 0.142.4.

Inventory [machine manifest](backend-reconciliation.json) memverifikasi 139 source Python terhadap parent pemiliknya sebelum perbaikan portabilitas di bawah. Seluruh frozen wire schemas dan Python contracts/ports 1.0.0 tetap byte-identical terhadap kedua parent. Tidak ada otomatisasi untuk menginstal handler B pada host A.

## Portabilitas pemeriksaan

Collection B harus memakai `.venv/bin/python -m pytest`, karena beberapa test mengimpor script dari root repository. Pemanggilan console pytest pada environment ini gagal collection; bukan hasil acceptance yang lulus.

Delapan kegagalan B berikutnya ditelusuri: harness worker memakai temporary path macOS dengan ancestor symlink `/var`; smoke fixture manifest memiliki LF tetapi hash B berasal dari CRLF Windows. Harness sekarang memakai canonical resolved scratch root, sementara guard runtime tetap menolak symlink. Smoke hanya menerima dua hash exact fixture LF/CRLF; perubahan byte lain tetap ditolak. Regression parametrized membuktikan keduanya dan tamper rejection dengan SDK MOCK, tanpa cloud call. Source overlay dan hash akhir tercatat pada manifest. FFmpeg/ffprobe 9.0.2 dipasang melalui Homebrew untuk menjalankan real local audio tests; shell profile tidak diedit.

## Reproduksi checks

Dari root repository, Python 3.12 dan FFmpeg/ffprobe 9.0.2 tersedia:

```sh
uv sync --locked
.venv/bin/python -m pytest tests/platform -q
.venv/bin/python -m pytest tests/analysis -q
.venv/bin/python -m flowlens.testing --track A
.venv/bin/python -m flowlens.testing --track B
.venv/bin/python -m flowlens.testing.acceptance --output artifacts/reports/reconciliation-b-acceptance.json
.venv/bin/ruff check backend tests scripts
.venv/bin/ruff format --check backend tests scripts
.venv/bin/mypy
.venv/bin/python -m flowlens.contracts.generate --check
.venv/bin/bandit -r backend/flowlens -ll
.venv/bin/pip-audit --local
.venv/bin/uv lock --check
.venv/bin/uv build --out-dir artifacts/reports/reconciliation-dist
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python scripts/package_smoke.py --wheel artifacts/reports/reconciliation-dist/atc_flowlens-0.1.0-py3-none-any.whl --sdist artifacts/reports/reconciliation-dist/atc_flowlens-0.1.0.tar.gz --output artifacts/reports/reconciliation-installed.json
.venv/bin/python scripts/checks/scan_secrets.py --report artifacts/reports/reconciliation-tracked-secrets.json
.venv/bin/python scripts/checks/scan_secrets.py --staged --report artifacts/reports/reconciliation-staged-secrets.json
```

Performed final results: platform **720 PASS, 1 opt-in capacity skip**; analysis **654 PASS**; contracts **66 PASS per track A/B**; B local acceptance **9 commands PASS**; Ruff check/format **207 files PASS**, mypy **139 source files PASS**, schema drift/lock/Bandit medium-high/build/clean installed wheel/native startup PASS. Dependency advisory audit: no known vulnerabilities (project unpublished skipped). Native startup health/release/OpenAPI200, ready503 tanpa coordinator, unauthenticated catalogue401; owned process dan temporary roots dibersihkan. Original A10 benchmark dipertahankan, tidak diklaim sebagai benchmark runtime gabungan baru. Final secret scan:467 tracked files dan109 staged files,0findings; staged diff check PASS. Raw log/disposable outputs berada pada ignored `artifacts/reports/reconciliation-*`. Signature scan terbatas pada pola PEM/Google/AWS/GitHub/Slack; bukan entropy/history certification. Bandit `-ll` menguji medium/high. Dependency advisory audit tidak mengaudit project unpublished sendiri.

## Status dan entry menuju integrasi

A01–A10 standalone selesai pada candidate A, dengan [acceptance](../testing/a101-evidence.md), [benchmark](../testing/a102-benchmark.json), [manifest A](package-a-manifest.json), dan [handoff A](package-a-handoff.md). Evidence ini tetap historical candidate A; checker manifest A terhadap joint checkout sengaja mendeteksi tambahan source/dependency B. Jangan regenerate snapshot A untuk menyatakan benchmark lama sebagai benchmark joint runtime. Source A, 18 migration A dan evidence A dipertahankan.

B01/B02 standalone selesai; B03–B06 mempunyai source dan local/MOCK engineering acceptance, tetapi external/provider/held-out/domain acceptance masih terbuka: [execution B](package-b-execution.md), [compatibility B](package-b-compatibility.md), [evidence B06](../testing/b06-evidence.md). Build/tests serta real FFmpeg lokal tidak membuktikan akses atau kualitas Google STT/Gemini. Provider verified **NO**, domain **NOT_DOMAIN_VALIDATED**, operational validation **NO**. G-BE/G-FE/G-DELIVERY `not_started`; Phase 10 `planned`.

Next action konkret: review PR `feat/backend-aben` → `feat/backend` sebagai source reconciliation, lalu pihak A/B menyelesaikan entry dependencies dan composition dengan bukti terpisah:

1. B menyediakan approved STT/Gemini profile/account/model/region/locale/quota/budget/rights, actual smoke dan held-out/domain evidence yang masih pending.
2. Bind explicit host StagePolicy, repositories, scoped context, provider adapters, HTTP/internal worker transport, snapshot dan purge inventories. Default B registrations tidak memiliki production routes/job handlers/snapshot reader, readiness tetap false/MOCK.
3. Project private B intent/advisory/provenance ke frozen DTO/evidence/JobResult dan validasi semantik/scope; jangan mengubah frozen 1.0.0 diam-diam.
4. Order A migrations dan analysis0001–0004 dalam API-owned UOW; reconcile B-aware maintenance/schema/catalog/backup/restore. CLI standalone A masih menolak unknown B ledger.
5. Jalankan integrated API/SQLite/authenticated worker/scenario/isolation/failure/retention/recovery, timing/capacity aktual, kemudian OpenAPI/client freeze dan review G-BE. Fake B atau source coexistence tidak menutup gate.

Pekerjaan ini tidak membuat frontend, container, deployment, real provider calls, ataupun mengubah branch target melalui merge PR.
