# BE-05 — Private audio assets dan job dispatch

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Mendaftarkan audio replay privat dan mengantrekan typed worker job/attempt tanpa memblokir simulation clock atau membuat writer kedua.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Tidak ditemukan AudioAsset/TranscriptionJob/worker dispatch di backend; runtime SQLite dimiliki server.

**TARGET:** Audio registration/authorized playback, asset/job persistence, dispatch/cancel/timeout dengan stub worker. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [backend/storage.py](../../../../backend/storage.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.1/time, §14.1 dan §14.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/app.py`

**File baru usulan, belum ada:** `backend/assist_service.py`, `backend/assist_storage.py`

Asset metadata DTO milik AI-01; BE owns file validation/job state/storage/transport. Inference worker milik AI-02/03. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App setelah BE-04; assist_service/storage edits berikut BE-06 lalu BE-07.

## 4. Kontrak dan dependency

**Contract:** SC-04/06 dan C-04/C-05/C-06. SC-04 AudioAsset/Job/WorkerRequest; C-04 scoped audio playback; C-05 fixed analysis input and C-06 worker protocol. Consumer AI-02, FE-02/05.

**Implementation dependency:** [BE-01](../backend/BE-01-contracts-ports-composition.md), [BE-04](../backend/BE-04-scoped-replay-api-stream.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** StubWorker queue dengan clock yang diinject, synthetic WAV atau validated private temp file; null alignment allowed untuk review-only unaligned segments.

**Integration dependency:** AI-01/02 worker DTO/process, BE-06 result sink dan FE-05 playback.

## 5. Pendekatan implementasi

1. Validate asset/source relation dan usage metadata sebelum queue; hash server-side, simpan raw file di runtime/private-audio dengan opaque ID, tidak di dist/static.
2. Persist asset+queued job+attempt atomik; job config/input hash/model version fixed C-05. Playback stream mengakses opaque ID sesudah token/scope validation, tanpa menerima path browser.
3. Dispatch typed local queue request di luar lock clock; worker tidak mempunyai Archive/DB/token operator.
4. Implement cancel/timeout/retry transitions SC-04 dan diagnostic safe; deadline menggunakan wall monotonic time, bukan sim_ms.
5. File registration/cleanup failure tidak mengembalikan success palsu; cancelled/old attempt result nanti ditolak BE-06. Tanpa local model, job explicit unavailable; tidak cloud fallback.

## 6. Output yang harus diserahkan

Private audio/job service dan storage, typed dispatch port, scoped playback dan job status untuk AI/FE; replay reader tetap mandiri saat job gagal.

## 7. Asumsi dan unknown

**ASSUMPTION:** Baseline synthetic WAV/audio fixtures dan same-host multiprocessing queues; model provisioned sebelum inferensi riil.

**UNKNOWN:** Actual model timeout/config/hardware; deadline adalah explicit job config, tanpa angka buatan. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 memiliki job/audio tests dengan worker stub. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Job | Valid synthetic asset+source capability | `python -m pytest tests/integration/test_be_05.py` | Queued asset/job committed sebelum dispatch; playback hanya asset pada source yang diizinkan. |
| Negative | Invalid file/hash, scope mismatch, cancel/timeout | Command sama | No dispatch sebelum validasi; failed/cancelled attempt tetap terminal. |
| Isolation | Worker stub lambat dan paused replay | Command sama | Clock/read API masih responsif; timeout memakai wall clock; worker tidak menulis DB. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Process worker | AI-02 process dan BE-06 sink | `python -m pytest tests/integration/test_worker_lifecycle.py` | Cancel/retry/late output tidak menggandakan commit atau mengubah source replay. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
