# SD-01 — Explicit geometry dan detector domain contract

**Owner-role:** Simulation/Detection

**Packet induk:** [simulation-detection.md](../../packages/simulation-detection.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghilangkan dependency detector pada private catalogue melalui public geometry input dan DTO observed-only.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** detection.py mengimpor LAYOUT dari scenarios.py dan membangun global PROTECTED; Track/Clearance typed sudah ada di models.py.

**TARGET:** Domain input/result types dan geometry validation/public layout adapter; baseline coordinates tetap. Tidak mengedit Session/Archive/API, menjalankan ASR, atau mengambil keputusan operasi.

## 3. Context dan ownership

- [backend/detection.py](../../../../backend/detection.py)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [backend/models.py](../../../../backend/models.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.2, §7.2–7.4, §7.8.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/detection.py`

**File baru usulan, belum ada:** `backend/geometry.py`, `backend/detection_contracts.py`

Tidak mengedit models.py milik BE; DTO SC-03 milik SD. Geometry menerima layout public, bukan importing private scenario. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. detection.py diedit SD-01→SD-03→SD-04→SD-05; semua task lain dapat menulis modulnya dengan geometry stub.

## 4. Kontrak dan dependency

**Contract:** SC-03 dan C-01/C-02/C-05. Public layout+Track/Clearance/config/time/coverage→ObservedDetectorInput/DetectionResult; names predictions/candidates/runway current dipertahankan untuk BE.

**Implementation dependency:** Tidak ada output implementasi task lain yang wajib tersedia. Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Inline valid/invalid polygon layout dan typed track state; no FastAPI/SQLite/Simulator instance.

**Integration dependency:** BE-01 ports dan BE-02 reducer sebagai consumer.

## 5. Pendekatan implementasi

1. Definisikan public layout types, physical runway/direction map, local axes/metres/version tanpa initial mobiles/actions.
2. Validasi polygons/dimensions/finite values; construction failure menjadi typed quality/input error dan tidak safe result.
3. Ubah footprint/protection helpers untuk menerima geometry explicit; baseline geometry values sama dengan LAYOUT current.
4. Definisikan ObservedDetectorInput/DetectionResult dan wrapper current signature untuk compatibility synthetic; private labels tidak ada pada types.
5. Pastikan dependency geometry/detector contracts tidak mengimpor Simulator, Session, Archive atau private catalogue.

## 6. Output yang harus diserahkan

Domain DTO dan explicit geometry helpers untuk SD-03/04 serta BE composition; geometry error dapat diteruskan sebagai degraded state.

## 7. Asumsi dan unknown

**ASSUMPTION:** Local Cartesian heading terhadap +x counterclockwise; 09/27 satu physical runway pada baseline.

**UNKNOWN:** Site-specific geometry/SOP dan geodetic transform mitra. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki domain contract/geometry validation tests. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Contract | F-GEOMETRY-01 valid layout+tracks | `python -m pytest tests/contracts/test_sd_01.py` | Fields/unit/direction mapping utuh; baseline footprint coordinates sama. |
| Negative | Invalid polygon/NaN/unknown physical direction | Command sama | Invalid input rejected/quality error; tidak memakai global synthetic fallback. |
| Isolation | Changed private schedule, same public input | Command sama | DTO/helpers dapat dipanggil tanpa private imports; result tidak menerima future plans. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Input injection | BE-02 reducer + public layout | `python -m pytest tests/integration/test_detector_geometry.py` | Imported public geometry yang dipilih digunakan, tanpa membaca global LAYOUT. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
