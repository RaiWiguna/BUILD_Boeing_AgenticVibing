# QA-01 — Canonical fixtures dan independent oracles

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** Fixture data QA-01 tersedia di area ownership pada 6 Oktober 2026. Pemeriksaan integritas data tercatat; suite QA-02, consumer integration, domain review, dan validasi operasional belum tersedia/dilakukan.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan versioned public replay/assist bundles dan private evaluator labels yang dapat dipakai semua workstream tanpa menunggu runtime.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (6 Oktober 2026):** Katalog source memiliki 12 scenario IDs. Fixture QA-06 `benchmark-manifest.json` sudah ada sebelumnya dan tetap milik QA-06. Bundle kanonis QA-01 kini ada. Contoh waktu C-03 yang executable memakai alert setelah delayed track receipt.

**TARGET:** Fixtures F-REPLAY/QUALITY/GEOMETRY/COMM/AI-FAIL/AUTH/REVIEW/STREAM dan numerical/time/evidence oracle independen. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [backend/data/scenarios.json](../../../../backend/data/scenarios.json)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [backend/models.py](../../../../backend/models.py)
- [backend/detection.py](../../../../backend/detection.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7, §15.1–15.7, §16.2–16.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Output QA-01:** `tests/fixtures/replay/` (kecuali manifest QA-06), `tests/fixtures/assist/`, dan `tests/fixtures/private/` berisi authored fixtures serta exact-byte SHA-256 manifests.

Public fixture bundle tidak memuat evaluator truth/future schedule; actual outcome expectations dibuat sebelum diuji dan tidak memanggil predict/detect/provider. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01–07 dan C-01–C-08. Canonical authored manifest/events/frames/audio metadata/stub results/expected values→semua task tests/mocks; content hash/version labels ikut bundle.

**Implementation dependency:** Tidak ada output implementasi task lain yang wajib tersedia. Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Fixture literal SC tanpa imports produksi; deterministic authored corpus/no-speech clips optional, transcript stub explicit.

**Integration dependency:** QA-02 suites dan QA-03/05 consumers; provider nyata hanya memakai labeled corpus yang terpisah.

## 5. Pendekatan implementasi

1. Buat bundle metadata/hash/version/source labels dan expected IDs/time/order; source masks coverage/missingness explicit.
2. Supply F-GEOMETRY analytical formulas/polygon reference per body/route, stationary/tangent/disjoint/reciprocal/error-only cases; no detector self-oracle.
3. Supply F-COMM-01 IDs canonical dan corrected executable timing C-03; raw/corrected transcript, linked versus possible_link, unknown confidence/speaker/negation variants.
4. Isolate private trajectories/benchmark/slot labels; public test/mock API cannot read private fixture root. Negative fixtures action/dangling refs remain deliberate invalid cases.
5. Define catalog mapping per all 12 IDs and fixed seeds/adequate-observation strata per plan; fixtures tuning versus evaluation terpisah; no measured accuracy claim.

## 6. Output yang harus diserahkan

Canonical public/private fixture bundle+independent authored expected values untuk contract/unit/browser/benchmark consumers; ini data/oracle, bukan test source atau hasil runtime.

## 7. Asumsi dan unknown

**ASSUMPTION:** Synthetic authored fixture corpus represent repeatability only; timing adjustment C-03 recorded without editing canonical docs.

**UNKNOWN:** Authorized partner corpus/license/domain-reviewed labels belum ada. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 owns executable fixture validation suite; QA-01 only creates data/expected references, no tests source. Target acceptance commands remain as follows; aktual QA-01 checks are recorded in §9.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Fixture validation | All F-* bundles+hash/versions | `python -m pytest tests/contracts/test_fixtures.py` | Public refs valid, hash bytes match, invalid fixtures explicitly separated. |
| Oracle causality | C-03 observed 74180/received 74530/alert 74600 | Command sama | Detector input tersedia sebelum alert; source time/sample/receipt remain distinct. |
| Isolation | Public loader and private oracle root | Command sama | Private labels tidak terbaca mock server/provider/frontend import. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Consumers | Ports/adapters semua paket memakai same bundle | `python -m pytest tests/contracts` | Consumer parity/cross-source negatives match one fixture semantics; no fabricated expected pass. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.

## 9. Hasil QA-01 — 6 Oktober 2026

### Fixture source dan batas data

- Bundle public berisi `F-REPLAY-01`, pemetaan katalog seluruh 12 source scenarios, public source-only frames, `F-GEOMETRY-01`, dan `F-QUALITY-01`.
- Bundle assist berisi metadata tanpa audio bytes, satu transcript stub/mock, candidate entities, highlight, evaluator-only option, serta failure, authorization, review, stream, dan intentional-invalid fixture inputs. Provider/model tetap unavailable; data ini bukan hasil ASR.
- `tests/fixtures/private/` memuat scenario evaluator labels dan geometry/quality/time/evidence oracles hasil authoring sintetik. Private root tidak dicantumkan pada manifest public atau artifact hash public.
- Setiap manifest memberi fixture/schema version, label `SYNTHETIC / NOT OPERATIONALLY VALIDATED`, provenance, exact-byte SHA-256, sumber/timebase/coverage/layout, parameter seed yang relevan, dan status domain/operational `not_reviewed` / `not_validated`. Fixture ini bukan phraseology review, domain fidelity, atau operational validation.
- Inspeksi source: `backend/data/scenarios.json` memiliki 12 source IDs; `backend/scenarios.py` mendefinisikan geometri `LOCAL_METRES` dengan directions 09/27 ke runway fisik yang sama; `Track` current extra-forbid; `backend/detection.py` menilai stale dengan `now_ms - observed_ms > 3000`; `backend/session.py` mencatat event `sim_ms` pada waktu event/receipt. Fixture memakai profile target `replay-1` / `assist-1`; source saat ini belum mempunyai replay importer, AI harness, atau additive assist routes yang memuatnya.
- Canonical mapping mengikuti makna Rencana Teknis MVP §15.2. QA-06 `benchmark-manifest.json` saat ini memetakan S01 ke `overlap` dan S02 ke `safe_cross`, kebalikan dari makna kanonis S01 `safe_cross` / S02 `overlap`. File milik QA-06 tidak diubah; report/benchmark QA-06 yang ada tidak memakai independent QA-01 labels dan tidak menjadi metrik accuracy.

### C-03 dan independent oracle

`SEG-TWR-006` dipetakan ke 72.400 s; `EVT-CLR-021` tersedia pada 73.020 s; `EVT-TRK-088` mempertahankan observed 74.180 s dan received/event availability 74.530 s; oracle private menetapkan `ALRT-009` dihitung pada 74.600 s, 70 ms setelah receipt. Alert timing adalah authored expected value, bukan detector runtime output. Tidak ada fixture QA-01 yang memakai 74.220 s.

### Runner, pemeriksaan, dan dependency

- Runner/dependency diperiksa sebelum QA check: `python --version` → Python 3.13.14; `python -m pytest --version` → pytest 9.0.3; metadata versions menunjukkan Pydantic 2.13.3, Shapely 2.1.2, FastAPI 0.136.1, httpx 0.28.1, Playwright 1.60.0.
- `python -m pytest tests/contracts/test_fixtures.py` — **not run**; suite milik QA-02 belum ada (`Test-Path` false). QA-01 tidak membuat atau mengubah test source.
- Pemeriksaan data aktual (`python -` dari PowerShell here-string) memverifikasi parse JSON/JSONL, exact-byte hashes replay/assist/private, hash sumber katalog, 12 mapping source IDs, S11/S12 workflow-only tanpa hazard stratum, cutoff frame sebelum/tepat saat receipt, C-03 timestamps dan margin kausal 70 ms, serta pemisahan private oracle dari hash indexes public. Pydantic 2.13.3 `Track.model_validate` dan `Clearance.model_validate` menerima nested current DTO fixture; ini tidak memvalidasi outer `replay-1` importer/runtime. Pemeriksaan data ini bukan pytest/test pass, bukan build, dan bukan runtime verification.
- QA-03 integration suite dan QA-04 mock launcher belum tersedia; API replay/assist tambahan tidak tersedia. QA-05 suite memakai inline fixture QA-05 dan QA-06 benchmark memakai input synthetic lokal, bukan canonical QA-01 bundle.
- `requirements.lock` dan `wheelhouse/` masih tidak ada. QA-01 tidak menyelesaikan blocker offline packaging QA-06.

### Domain review dan validasi operasional

Trainer/ATCO review: **belum dilakukan**. Partner data/replay, provider/model output, fidelity domain, LAN integration, dan operational validation: **belum dilakukan**. Output QA-01 saat ini adalah source fixture dan authored oracle data saja.
