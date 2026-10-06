# BE-05 — Private audio assets dan job dispatch

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** SOURCE IMPLEMENTED pada 4 Oktober 2026; tujuh integration tests dan pemeriksaan scoped lulus (rincian §8). Belum terhubung ke process worker/provider AI; tidak ada audio mitra atau validasi operasional.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Mendaftarkan audio replay privat dan mengantrekan typed worker job/attempt tanpa memblokir simulation clock atau membuat writer kedua.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE setelah BE-05:** `backend/assist_service.py` dan `backend/assist_storage.py` menyediakan registrasi audio privat dan job/attempt di atas koneksi SQLite milik `Archive`. `backend/app.py` mengikat layanan dan routes tambahan. Belum ada provider/model AI atau worker process AI-02.

**DELIVERED:** Registrasi PCM WAV untuk imported replay dengan source/timebase/coverage/provenance/permission metadata yang cocok; hash dihitung server; file opaque disimpan di private runtime directory; asset/job/attempt disimpan sebelum worker dispatch; playback dan status scoped; cancel/timeout/retry menjaga attempt aktif. Worker default/config yang tidak ada membuat job gagal dengan alasan aman. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [backend/storage.py](../../../../backend/storage.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.1/time, §14.1 dan §14.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/app.py`

**File baru pada deliverable ini:** `backend/assist_service.py`, `backend/assist_storage.py`

Asset metadata DTO target milik AI-01; karena DTO itu belum tersedia, BE-05 memakai adapter lokal yang mengikuti SC-04. BE owns file validation/job state/storage/transport. Inference worker milik AI-02/03 dan belum terpasang. App setelah BE-04; assist_service/storage edits berikut BE-06 lalu BE-07. `tests/integration/test_be_05.py` dibuat untuk verifikasi task ini sesuai instruksi deliverable.

## 4. Kontrak dan dependency

**Contract:** SC-04/06 dan C-04/C-05/C-06. SC-04 AudioAsset/Job/WorkerRequest; C-04 scoped audio playback; C-05 fixed analysis input and C-06 worker protocol. Consumer AI-02, FE-02/05.

**Implementation dependency:** [BE-01](../backend/BE-01-contracts-ports-composition.md), [BE-04](../backend/BE-04-scoped-replay-api-stream.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** StubWorker queue dengan clock yang diinject, synthetic WAV atau validated private temp file; null alignment allowed untuk review-only unaligned segments.

**Integration dependency:** AI-01/02 worker DTO/process, BE-06 result sink dan FE-05 playback.

## 5. Pendekatan implementasi

1. Multipart menerima field `audio` dan field string `metadata` JSON dengan field SC-04 selain ID/duration/hash/path server-owned. Metadata harus terikat pada source import, channel/coverage, timebase, provenance, usage profile, dan retention yang sama. Baseline memvalidasi PCM WAV 1–2 channel, sample width 1–4 byte, positive sample rate/duration, serta batas upload 64 MiB; codec lain belum didukung.
2. Implementasi menghitung SHA-256, menulis file staging lalu rename ke ID opaque di `runtime/private-audio`, kemudian meng-commit asset, job, dan attempt pertama dalam satu transaksi pada koneksi `Archive.db`. Bila transaksi gagal, file dibersihkan; file/path tidak masuk respons publik.
3. Worker port memakai `asyncio.to_thread` agar panggilan sync tidak menahan event loop/lock simulation. Request immutable berisi ID/attempt/asset, validated private file reference/hash, provider/model/config version, timebase dan alignment; tidak berisi DB, Archive, actor/token, checkpoint, simulator truth, command, atau production feed. Process-isolation/spawn queue tetap dependency AI-02 yang belum tersedia.
4. `GET .../transcription-jobs/{job_id}` membaca status/attempt; `POST .../{job_id}/cancel` dan `POST .../{job_id}/retry` adalah endpoint additive pilihan BE-05. Retry hanya dari `failed`/`cancelled` dan membuat `attempt_id` baru. Deadline perlu `AssistJobConfig.timeout_s` eksplisit dan memakai injected monotonic clock, bukan `sim_ms`.
5. Worker/config yang belum dikonfigurasi menghasilkan job `failed` dengan diagnostic aman `job_configuration_unavailable` atau `worker_unavailable`. Tidak ada cloud fallback, inference, transcript, atau candidate yang dibuat. Hash mismatch, exception worker, timeout, cancel, dan stale attempt memberi transisi aman; hanya hasil attempt aktif yang diterima.
6. `GET .../audio-assets/{asset_id}/content` memeriksa source scope sebelum lookup asset dan memverifikasi hash; `source_read_token` dapat memakai route ini dan job status pada source terikat, namun tidak command, seat, import, branch, atau cancel/retry.

## 6. Output yang harus diserahkan

Private audio/job service dan storage, typed dispatch port, scoped playback dan job status untuk AI/FE; replay reader tetap mandiri saat job gagal.

## 7. Asumsi dan unknown

**ASSUMPTION:** Test baseline memakai WAV sintetik dan fake worker. Test adapter berjalan di thread melalui `asyncio.to_thread`; belum mengklaim process isolation atau multiprocessing queue.

**UNKNOWN / batas tersisa:** AI-01 DTO dan AI-02 process queue belum tersedia; adapter BE bersifat lokal. Model/provider/config/hardware riil dan timeout production tidak tersedia; hanya injected test `AssistJobConfig.timeout_s` mengaktifkan dispatch. Format audio hanya PCM WAV dan limit 64 MiB. Tidak ada audio mitra, attestation permission operator yang independen, ASR, domain review, atau operational validation. Tujuh test menggunakan WAV fixture sintetik dan fake worker.

## 8. Test dan kriteria lulus

BE-05 verification dijalankan pada 4 Oktober 2026 melalui test mandiri dengan `TestClient`, SQLite sementara, fake wall/monotonic clock, actor/token uji, WAV PCM sintetik, dan fake worker. Tidak memakai database runtime, operator credential nyata, audio mitra, atau model eksternal.

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

Hasil aktual: `python -m pytest tests/integration/test_be_05.py` — lulus, 7 tests; Ruff command di atas — lulus dengan pengecualian legacy `B008,UP041`; scoped mypy command di atas — lulus pada empat file dengan imported modules dilewati; `git diff --check` — exit 0 dengan notifikasi line-ending `backend/app.py`. Stub pass dilaporkan terpisah dari integration/provider riil.

Process-worker check `python -m pytest tests/integration/test_worker_lifecycle.py` belum dijalankan karena AI-02 process worker dan BE-06 result sink belum tersedia. TestClient membuktikan runtime pada harness sementara saja; tidak ada build, deployment, provider inference, review domain, audio partner, atau validasi operasional yang dinyatakan berhasil.
