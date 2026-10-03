# BE-04 — API replay, read service, dan stream terotorisasi

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Melayani import, historical frames/events/evidence dan review controls sesuai token scope, mempertahankan API/stream synthetic existing.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Manager snapshot melakukan role/baseline redaction; Review token terikat review ID; source lookup dengan token itu ditolak. Review annotation/control receipt in-memory.

**TARGET:** Additive replay routes, imported read-only review, credential source-read terpisah, pagination/resync. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [backend/review.py](../../../../backend/review.py)
- [backend/storage.py](../../../../backend/storage.py)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §12.4, §13, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/app.py`, `backend/review.py`

**File baru usulan, belum ada:** Tidak ada file source baru di task ini.

Tidak memperluas authority command dari source-read capability; private checkpoint/truth tidak ada pada evidence reader. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/review edits setelah BE-01; route additions berikutnya BE-05→BE-06→BE-07→BE-08 agar file yang sama tidak ditulis paralel.

## 4. Kontrak dan dependency

**Contract:** SC-01/02/06. SC-06 existing routes + replay-import/replay-source; C-02 frame/evidence reads; C-04 credential source-read dan audio scope; consumer FE-02.

**Implementation dependency:** [BE-01](../backend/BE-01-contracts-ports-composition.md), [BE-02](../backend/BE-02-replay-source-state-reducer.md), [BE-03](../backend/BE-03-atomic-replay-import-archive.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** FakeReplayArchiveReader dengan recorded frames, scoped actor fixtures dan imported review state; source reader riil diperlukan hanya integration.

**Integration dependency:** BE-03 SQLite source service, FE-02 API adapter dan QA-03/05.

## 5. Pendekatan implementasi

1. Expose import multipart dan replay-source public projection; source identity tetap stable meskipun Review ID ephemeral.
2. Tambah replay-frame/evidence endpoints C-02 dengan explicit time/analysis scope; historical state tidak dihitung ulang oleh client atau current model.
3. Extend review control untuk imported replay tanpa private simulator checkpoint; SEEK value seconds dan revision tetap current. Reject simulator mutation pada frozen/imported source.
4. Create review mengembalikan source-read credential terpisah sesuai C-04; source token tidak mendapat command privilege/evaluator truth.
5. Filter event/source projection sesuai role/condition/time; pagination cursor atas inspected source rows, tanpa future leakage. Main WS first-message auth/direct snapshot tetap unchanged; reconnect resync.

## 6. Output yang harus diserahkan

Scoped REST/review reads dan main stream compatibility untuk FE adapter; unresolved evidence response eksplisit, bukan fabricated event.

## 7. Asumsi dan unknown

**ASSUMPTION:** Evaluator baseline menggunakan instructor replay capability, enum Role current dipertahankan.

**UNKNOWN:** Identity policy organisasi mitra tidak dibutuhkan untuk scoped synthetic seats. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 memiliki API/WS tests; external detector/worker stub. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| API | Frozen synthetic/imported source + scoped instructor | `python -m pytest tests/integration/test_be_04.py` | Frame <= requested time; metadata/source/review IDs benar; cursor tidak kehilangan same-time event. |
| Negative | Cross-source, expired, baseline and observer actors | Command sama | 401/403/404 sesuai scope; private/AI evaluator data tidak bocor. |
| Compatibility | Current login/Command/direct WS snapshot | Command sama | target/runway/revision/kind lowercase dan first-message token tetap diterima. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Reconnect/UI | FE-02 API adapter + BE archive | `python -m pytest tests/browser/test_api_reconnect.py` | Latest authorized snapshot mengganti stale view; gap tidak membuat fabricated delta. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
