# QA-01 — Canonical fixtures dan independent oracles

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan versioned public replay/assist bundles dan private evaluator labels yang dapat dipakai semua workstream tanpa menunggu runtime.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Catalogue mempunyai 12 synthetic scenario IDs; tests/fixtures belum ditemukan. Contoh SYN-COMM illustrative mempunyai alert time sebelum delayed track receipt.

**TARGET:** Fixtures F-REPLAY/QUALITY/GEOMETRY/COMM/AI-FAIL/AUTH/REVIEW/STREAM dan numerical/time/evidence oracle independen. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [backend/data/scenarios.json](../../../../backend/data/scenarios.json)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [backend/models.py](../../../../backend/models.py)
- [backend/detection.py](../../../../backend/detection.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7, §15.1–15.7, §16.2–16.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `tests/fixtures/replay/`, `tests/fixtures/assist/`, `tests/fixtures/private/`

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

Canonical public/private fixture bundle+independent expected values untuk all contracts/unit/browser/benchmark checks.

## 7. Asumsi dan unknown

**ASSUMPTION:** Synthetic authored fixture corpus represent repeatability only; timing adjustment C-03 recorded without editing canonical docs.

**UNKNOWN:** Authorized partner corpus/license/domain-reviewed labels belum ada. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 owns executable fixture validation suite; QA-01 only creates data/expected references, no tests source. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

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
