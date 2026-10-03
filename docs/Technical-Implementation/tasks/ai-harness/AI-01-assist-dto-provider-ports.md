# AI-01 — Assist DTOs dan provider ports

**Owner-role:** AI Harness

**Packet induk:** [ai-harness.md](../../packages/ai-harness.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan schema transcript/entities/highlights/options/annotations dan provider ports yang menolak action fields serta evidence references ambigu.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Tidak ada assist schema/providers di backend; models.py memuat current simulator contracts extra-forbid.

**TARGET:** SC-04/05 executable DTOs dan ASRProvider/SummaryProvider signatures dengan deterministic stubs. Tidak membuka database sesi, memanggil command/clearance, mengubah severity, atau memakai audio live.

## 3. Context dan ownership

- [backend/models.py](../../../../backend/models.py)
- [backend/session.py](../../../../backend/session.py)
- [backend/detection.py](../../../../backend/detection.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.2, §7.1–7.2, §10.4, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `backend/assist_contracts.py`, `backend/ai_harness/providers.py`, `backend/ai_harness/__init__.py`

AI memiliki domain schemas/provider payloads; BE memiliki storage/transport. DTO import tidak menyalakan model/DB/client. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. providers.py diperkenalkan AI-01 lalu AI-03 dan AI-05; ai_harness package marker diperkenalkan di sini.

## 4. Kontrak dan dependency

**Contract:** SC-04/05 dan C-04–C-08. WorkerRequest/Result, AudioAsset/Job, TranscriptSegment, CandidateEntity, Highlight, Option, Annotation DTO; provider read-only signatures untuk BE/AI-02–05/FE mirror.

**Implementation dependency:** Tidak ada output implementasi task lain yang wajib tersedia. Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** StubASR dan StubSummary output `stub-1`, nullable confidence, typed public refs; no provider download.

**Integration dependency:** BE-05/06 transport/storage validation dan AI worker pipeline.

## 5. Pendekatan implementasi

1. Definisikan Pydantic extra-forbid DTO mengikuti SC, exact field naming/version refinements C-05/07/08 dan typed evidence refs.
2. Audio-relative start/end finite integer dan order valid; confidence null berarti unavailable, speaker_source distinguishes metadata/hypothesis.
3. Entity instruction adalah candidate string, bukan Clearance. Option schema menolak command/control_action/clearance execution payload.
4. Definisikan provider ports dengan model/config/input versions explicit, progress/errors typed, no tool capability.
5. Implement deterministic provider stubs tanpa automatic availability/inference claim; optional model modules lazy-loaded kelak.

## 6. Output yang harus diserahkan

Assist schemas/provider interfaces dan stubs, termasuk package marker `backend/ai_harness/__init__.py` usulan, untuk semua assist consumers.

## 7. Asumsi dan unknown

**ASSUMPTION:** Worker/output JSON snake_case; exact states mengikuti SC/addendum.

**UNKNOWN:** Calibration confidence dan actual models/licenses. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki schema/port contract tests. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Contract | Valid segments/options + typed refs | `python -m pytest tests/contracts/test_ai_01.py` | Round-trip fields/model/time/uncertainty utuh; null confidence tetap null. |
| Negative | Extra action, invalid interval/confidence, foreign refs | Command sama | Schema invalid ditolak; reference scope divalidasi sink/reconciliation, tidak dianggap fakta hanya karena JSON valid. |
| Isolation | Import DTOs/stub calls tanpa providers installed | Command sama | No DB/process/download; stub output jelas authored/stub. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Producer/consumer parity | BE-06 result sink + AI DTOs | `python -m pytest tests/integration/test_assist_dto_parity.py` | Same schema accepted/rejected pada worker dan server; no duplicate DTO meaning. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
