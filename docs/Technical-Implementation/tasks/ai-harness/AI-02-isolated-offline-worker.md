# AI-02 — Process-isolated offline worker

**Owner-role:** AI Harness

**Packet induk:** [ai-harness.md](../../packages/ai-harness.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menjalankan pipeline worker di proses terpisah dengan typed queues dan explicit attempts sehingga inference tidak memblokir session server.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Backend clock adalah coroutine FastAPI; belum ada AI process/IPC atau worker module.

**TARGET:** Worker entrypoint, request/progress/result protocol, cancellation/resource lifecycle; provider stub default. Tidak membuka database sesi, memanggil command/clearance, mengubah severity, atau memakai audio live.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.3 single writer, §7.5, §14.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `backend/ai_harness/worker.py`

Worker tidak membuka SQLite, menerima token atau membaca private checkpoints. BE-05 memiliki queue dispatch, deadline dan terminal state job. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-04/05 dan C-06. Typed WorkerRequest/attempt/config→progress/WorkerResult; input read-only local asset and evidence slice; no response commit authority.

**Implementation dependency:** [AI-01](../ai-harness/AI-01-assist-dto-provider-ports.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Slow/failing/no-speech StubASR/summary, dummy result sink/asset fixture; no BE app required.

**Integration dependency:** BE-05/06 job service/sink dan AI-03–05 pipeline.

## 5. Pendekatan implementasi

1. Implement Windows-safe spawn process entrypoint dengan request/result multiprocessing queues C-06; bounded capacity config explicit dan no async blocking queue get di server.
2. Validate DTO/asset/hash/model config sebelum process inference; asset references originate validated service, not free filesystem path.
3. Emit typed progress/chunk outputs dan final result tagged job/attempt/input versions; provider failure safe diagnostic.
4. Cancellation checked antar-chunk; timeout/forced worker stop menutup resources dan late results discarded by server; tidak memutar ulang cancelled attempt.
5. Shutdown closes process/queues; providers lazy constructed di worker, no SQLite/production network/command clients.

## 6. Output yang harus diserahkan

Isolated worker runtime entrypoint/lifecycle dan protocol-compatible stub pipeline untuk BE integration.

## 7. Asumsi dan unknown

**ASSUMPTION:** Local process/queue cukup baseline; chunk/deadline configuration explicit, no arbitrary model quality threshold.

**UNKNOWN:** Actual inference latency/hardware dan chunk tuning riil. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 owns worker unit harness; QA-03 process integration. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Worker | Deterministic valid request + stub | `python -m pytest tests/unit/test_ai_02.py` | Result mempunyai matching IDs/versions; no writer or command side effect. |
| Negative | Cancel/exception/bad input/late attempt | Command sama | Safe failure terminal signal; resources closed; raw invalid output tidak dianggap accepted. |
| Boundary | Slow provider+recorded progress | Command sama | Worker/progress clocks terpisah replay clock; BE validation/commit tetap downstream. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Clock isolation | BE server advancing/read + slow worker | `python -m pytest tests/integration/test_worker_lifecycle.py` | Session read/clock tetap usable; failed/cancelled/late attempt tidak duplicate commit. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
