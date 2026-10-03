# QA-06 — Offline package dan benchmark evidence

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan paket lokal yang cold-run tanpa download dan laporan technical benchmark yang memisahkan compute/delivery/replay/AI measurements.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** pyproject versions belum lock penuh; frontend dist/index.html dan model assets tidak ditemukan pada inspeksi; report detector timing recent bukan LAN/study result.

**TARGET:** Offline packaging/backup/version manifest, synthetic cold-run tests, benchmark/endurance and optional ASR quality reporting. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [pyproject.toml](../../../../pyproject.toml)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [backend/storage.py](../../../../backend/storage.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §14.4, §15.3–15.7, §16.4–16.6, §18.7.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `scripts/package_offline.py`, `tests/integration/test_offline_package.py`, `tests/integration/test_performance.py`, `tests/fixtures/replay/benchmark-manifest.json`

QA package tooling/tests only; BE-08 owns backend provisioning/backup implementation, FE-01 owns build/lock, AI owns provider adapters. Benchmark manifest file reserved QA-06; QA-01 authors canonical data others. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. QA-03 tidak mengedit reserved tests/integration/test_offline_package.py/test_performance.py; benchmark manifest bukan file QA-01.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. Built frontend+runtime locks/source/schema/config/layout/scenario/model manifest→offline package and actual measured report; no unauthorized partner payload default.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-03](../integration-qa/QA-03-backend-worker-integration-failures.md), [QA-05](../integration-qa/QA-05-browser-replay-review-flows.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Stub-provider package valid explicitly mock-labeled; model missing test no download; canonical synthetic scenario bundle.

**Integration dependency:** BE-08 runtime+all feature outputs; ASR/provider real metrics conditional actual assets, no claiming validation from stubs.

## 5. Pendekatan implementasi

1. Implementasikan package_offline.py --output tmp/flowlens-offline; kumpulkan frontend build mode API, runtime locks serta version/hash manifest. Required artifact yang hilang menggagalkan packaging; AI opsional yang hilang tetap berlabel unavailable.
2. Jangan memasukkan credential/private truth/audio ke public static bundle; default package hanya data sintetik. Runtime membuat storage privat lokal; backup memakai SQLite backup API.
3. Cold-run dengan network disabled tanpa download/cloud fallback; uji source replay saat AI unavailable, lalu job/evidence/review saat model provisioned.
4. Benchmark 12 canonical scenarios dan 100 run pada plan: 40 conflict/40 safe/10 delay-noise/10 dropout. Bekukan seeds/parameter, pisahkan tuning/denominator; default tanpa intervention.
5. Ukur detector/delivery/render/reconnect/sync/endurance terpisah dengan environment manifest dan target kanonis. Metrics ASR/candidate per corpus/model hanya dilaporkan jika provider benar-benar dijalankan.

## 6. Output yang harus diserahkan

Paket offline sintetik dan laporan technical evidence aktual beserta batas klaim; tanpa deployment live atau klaim validasi domain/operasional.

## 7. Asumsi dan unknown

**ASSUMPTION:** Satu RUNNING session dengan baseline 5 aircraft+2 vehicles; model/dependency diprovision. Hasil localhost dan real LAN diberi label berbeda.

**UNKNOWN:** Cold-run compatibility, resource use, ASR quality dan fidelity data mitra belum diukur. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-06 owns reserved offline/performance tests; metrics are measurements to collect after runtime available. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Package inputs | Built UI+version locks and optional model missing | `python scripts/package_offline.py --output tmp/flowlens-offline` | Artifact manifest precise, credentials/private exports excluded; missing required artifact explicit failure. |
| Negative cold-run | Network disabled, optional model unavailable | `python -m pytest tests/integration/test_offline_package.py` | No downloads/cloud calls; source replay still usable and AI unavailable explicit. |
| Benchmark bookkeeping | Fixed strata manifests and independent labels | `python -m pytest tests/integration/test_performance.py` | No tuning/evaluation overlap or denominator removal; false occupancy warning excludes clearance-only advisory. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Performance/endurance | Complete runtime+hardware/browser/LAN manifest | `python -m pytest tests/integration/test_performance.py` | Plan targets assessed: detector p95<50ms, delivery/render p95<500ms, reconnect≤3s, LAN clock diff<500ms, endurance30min; unavailable LAN not reported pass. |
| Package lifecycle | Cold boot→replay/job/review→backup/restart | `python -m pytest tests/integration/test_offline_package.py` | Accepted events/receipts/revisions survive; source private/public isolation and no command option path. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
