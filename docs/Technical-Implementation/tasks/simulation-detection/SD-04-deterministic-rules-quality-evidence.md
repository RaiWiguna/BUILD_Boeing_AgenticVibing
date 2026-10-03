# SD-04 — Deterministic rules, data quality, dan evidence

**Owner-role:** Simulation/Detection

**Packet induk:** [simulation-detection.md](../../packages/simulation-detection.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan rule candidates dan runway quality yang membedakan nominal occupancy, buffer-only, permission inconsistency dan unknown coverage.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** detect mengeluarkan predictions/candidates/runway dan tujuh rule strings termasuk SWEPT_OCCUPANCY; expected_ids diisi Session dari private simulator roster.

**TARGET:** Observed-only rule port dengan coverage IDs publik dan evidence/result parity. Tidak mengedit Session/Archive/API, menjalankan ASR, atau mengambil keputusan operasi.

## 3. Context dan ownership

- [backend/detection.py](../../../../backend/detection.py)
- [backend/models.py](../../../../backend/models.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §9.6–9.7, §10.1–10.5, §16.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/detection.py`

**File baru usulan, belum ada:** Tidak ada file source baru di task ini.

SD memiliki candidate semantics; BE memiliki authoritative events/persistence. ASR instruction entity tidak masuk Clearance. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. detection.py sesudah SD-03 dan sebelum SD-05.

## 4. Kontrak dan dependency

**Contract:** SC-01/03. SC-03 ObservedDetectorInput→DetectionResult; candidate key/rule/version/objects/severity/metrics/ages/evidence/time/assumptions; consumer SD-05/BE/AI.

**Implementation dependency:** [SD-03](../simulation-detection/SD-03-footprint-occupancy-prediction.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Known intervals and structured clearances, F-QUALITY-01/F-GEOMETRY-01; no source feed/DB.

**Integration dependency:** SD-05 lifecycle dan BE-02 state/BE-03 storage.

## 5. Pendekatan implementasi

1. Pertahankan current rule strings/mapping R01–R06 dan separate SWEPT_OCCUPANCY; inject physical geometry/direction/coverage.
2. Nominal interval overlap menentukan occupancy rule; assumed range/buffer-only tetap advisory terpisah. Reciprocal 09/27 satu resource.
3. Hold violation/closed runway/clearance inconsistency memakai structured events/current and previous observations; request/cancel tidak menghapus physical occupancy.
4. Compute missing/stale/no-route quality dari public expected IDs dan sample ages; stale/last-known occupancy ditandai, tidak clear.
5. Attach resolvable source IDs/versions/time/assumptions; swept transit uncertainty explicit; no AI severity or duplicate hazard semantics.

## 6. Output yang harus diserahkan

Observed-only deterministic candidates/runway quality dengan evidence completeness untuk lifecycle/replay/reconciliation.

## 7. Asumsi dan unknown

**ASSUMPTION:** Baseline thresholds severity/lab SOP sesuai config/plan, belum standar operasi.

**UNKNOWN:** Procedure/local clearance compatibility mitra. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memetakan canonical rule outcomes dan independent intervals. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Rules | Overlap/buffer-only/reciprocal/hold/closed cases | `python -m pytest tests/unit/test_sd_04.py` | Rule/category/severity sesuai baseline; permission advisory tidak dihitung collision. |
| Negative | Unauthorized occupancy, missing/stale route, cancel | Command sama | Presence tetap dinilai tanpa clearance; unknown tidak berarti runway clear. |
| Evidence | Public source ID map dan calculated times | Command sama | Setiap relevant candidate punya valid evidence/version/objects/time; private truth tidak diperlukan. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| State/rules | BE-02 reducer+SD-05 lifecycle | `python -m pytest tests/integration/test_rule_lifecycle.py` | Delayed observations/hold events menghasilkan expected candidates pada receive clock, bukan future source sample. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
