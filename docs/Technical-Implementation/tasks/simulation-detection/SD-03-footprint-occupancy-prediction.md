# SD-03 — Footprint dan occupancy interval prediction

**Owner-role:** Simulation/Detection

**Packet induk:** [simulation-detection.md](../../packages/simulation-detection.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan occupancy/ETA deterministic dengan full footprint, route segments, aging dan unknown exit yang dapat dibandingkan oracle analitik.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** footprint/expanded_area/predict/threshold_eta tersedia, menggunakan global protection geometry dan route/current speed; stopped inside returns horizon exit_unknown.

**TARGET:** Explicit-geometry prediction implementation dan numerical boundary coverage tanpa perubahan threshold operasi. Tidak mengedit Session/Archive/API, menjalankan ASR, atau mengambil keputusan operasi.

## 3. Context dan ownership

- [backend/detection.py](../../../../backend/detection.py)
- [backend/models.py](../../../../backend/models.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §9, §16.2 dan §16.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/detection.py`

**File baru usulan, belum ada:** Tidak ada file source baru di task ini.

Tidak memanggil Simulator atau labels oracle; layout/config dari observed input. Rules severity diselesaikan SD-04. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. SD-01→SD-03→SD-04 pada detection.py.

## 4. Kontrak dan dependency

**Contract:** SC-01/03. Track/now_ms/geometry/config→SC-03 predictions dengan seconds relatif calculation time, model/source evidence. Consumer SD-04 dan BE archived frame.

**Implementation dependency:** [SD-01](../simulation-detection/SD-01-explicit-geometry-detector-contract.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** F-GEOMETRY-01 inline analytic body/routes/speed; geometry provider stub jika SD-01 belum dirangkai.

**Integration dependency:** SD-04 rules dan BE-02 archived analysis builder.

## 5. Pendekatan implementasi

1. Hitung full oriented footprint/intersection, expanded protection area dan route-distance intervals pada geometry yang diinject.
2. Apply sample age correction once, merge overlapping segments sambil mempertahankan disjoint intervals dan horizon.
3. Stationary/near-zero atau route ends inside menghasilkan exit_unknown; phase go_around/departed/downwind mengikuti model current.
4. Hitung threshold_eta sebagai threshold crossing, terpisah dari protection-entry dan overlap; attach calculated time, source event/model version.
5. Reject numeric invalid input; unknown route/time menjadi quality unknown tanpa fabricated precise prediction.

## 6. Output yang harus diserahkan

Prediction helpers/result intervals untuk rules/frames/evidence dengan explicit geometry dan quantitative oracle assertions.

## 7. Asumsi dan unknown

**ASSUMPTION:** Constant observed speed dan declared remaining route adalah asumsi eksperimen, bukan aircraft maneuver model.

**UNKNOWN:** Site-specific footprint/uncertainty calibration. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki numerical suite dengan oracle independen. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Numerical | Analytic ETA dan one-tick route references | `python -m pytest tests/unit/test_sd_03.py` | ETA sederhana error ≤1e−6 s; discrete timing beda ≤100 ms sesuai plan. |
| Boundary | Rotated/tangent/rear-exit/disjoint/route ends inside | Command sama | Body rear inside tetap occupied; unknown exit tidak berubah menjadi definite clear. |
| Negative | NaN/no route/stale/phase variants | Command sama | Quality/failure explicit; tidak membaca planned future speed/trajectory. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Prediction archive | BE-02/03+SD-04 | `python -m pytest tests/integration/test_prediction_archive.py` | Frame menyimpan exact calculation/source/config version; replay tidak re-run current model. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
