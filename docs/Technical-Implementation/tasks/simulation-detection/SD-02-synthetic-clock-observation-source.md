# SD-02 — Synthetic clock dan observation source adapter

**Owner-role:** Simulation/Detection

**Packet induk:** [simulation-detection.md](../../packages/simulation-detection.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan canonical source records repeatable dari sampling/delivery simulator, dengan clock, coverage dan checkpoints yang terpisah dari public observations.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Simulator mempunyai seeded RNG, sample delay queue, response timers dan checkpoint/restore; catalogue berisi 12 IDs serta public metadata.

**TARGET:** Synthetic ReplayEventSource, scenario validation, pause/speed/channel behavior dan private checkpoint compatibility. Tidak mengedit Session/Archive/API, menjalankan ASR, atau mengambil keputusan operasi.

## 3. Context dan ownership

- [backend/simulator.py](../../../../backend/simulator.py)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [backend/data/scenarios.json](../../../../backend/data/scenarios.json)
- [backend/models.py](../../../../backend/models.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.4–7.8, §8, §14.3, §15.1–15.3.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/simulator.py`, `backend/scenarios.py`, `backend/data/scenarios.json`

**File baru usulan, belum ada:** `backend/synthetic_source.py`

Public source read tidak mengeluarkan future actions/RNG; checkpoints hanya melalui BE private boundary. SYN-COMM paired annotations tetap fixtures QA-01. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01/03. Private scenario+seed/config→SC-01 manifest/events dan checkpoint opaque typed boundary; consumer BE-02 dan QA oracle evaluator.

**Implementation dependency:** [SD-01](../simulation-detection/SD-01-explicit-geometry-detector-contract.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Local event collector dan fake simulation controls; schema literals SC-01 ketika BE DTO belum diimplementasikan.

**Integration dependency:** BE-02/03 ingestion dan BE-08 branch restoration.

## 5. Pendekatan implementasi

1. Validate scenario IDs/routes/targets/timeline sebelum READY, mempertahankan 12 existing IDs dan public count/domain-review labels yang benar.
2. Fixed-step tick 100 ms, sample 1000 ms, configured delivery delay; pause freezes sim time, speed mengubah wall budget bukan dt.
3. Emit public sampled Track/structured session inputs ber-ID stabil fixture dan observed/received timestamps; coverage berasal public manifest.
4. Preserve seeded noise, dropout semantics dan response delays current; low visibility tidak otomatis mengubah surveillance coverage.
5. Checkpoint/restore RNG/queue/action index/route progress/pending physical responses; version metadata dipakai BE-08, tidak diekspor ke detector/FE.

## 6. Output yang harus diserahkan

Synthetic source adapter, validated scenario/channel behavior dan private checkpoint round-trip untuk BE; benchmark memakai seeds fixed.

## 7. Asumsi dan unknown

**ASSUMPTION:** Nilai tick/sample/stale tetap baseline lab config; compare repeatability menormalisasi UUID/audit wall time.

**UNKNOWN:** Real movement/channel fidelity dan format checkpoint vendor. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki clock/source unit tests; independent event schedule di QA-01. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Unit | Same seed/config controls dua run | `python -m pytest tests/unit/test_sd_02.py` | Observed values/order/delivery times sama setelah normalization identity/audit. |
| Negative | Unknown target, negative dimension, delayed/dropout fixture | Command sama | Invalid scenario sebelum READY; sampled packet tidak hilang diam-diam; observed time tidak diganti. |
| Clock | Pause/0.5×/1×/2×/4×+restore | Command sama | Pause tidak age; fixed-step physics/queue/response restore konsisten. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Branch | BE-08 source+child compatible frame | `python -m pytest tests/integration/test_branch_restore.py` | Parent immutable; child subsequent observed stream match reference sampai intervention. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
