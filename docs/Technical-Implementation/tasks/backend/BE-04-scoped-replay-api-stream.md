# BE-04 — API replay, read service, dan stream terotorisasi

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** Implementasi source BE-04 tersedia; lima test integrasi TestClient lulus pada 4 Oktober 2026. Belum ada review domain atau validasi operasional.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Melayani import, historical frames/events/evidence dan review controls sesuai token scope, mempertahankan API/stream synthetic existing.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE sebelum BE-04:** Manager snapshot melakukan role/baseline redaction; Review token terikat review ID; source lookup dengan token itu ditolak. Review annotation/control receipt in-memory.

**SOURCE BE-04:** `app.py` kini menyediakan multipart import melalui `ReplayImportService`, projection source/frame/evidence, paging events dengan cutoff sebelum limit, serta token source-read terikat source. `review.py` mendukung playback imported read-only dengan frame source-only dari event reader/reducer BE-02; analysis hanya disajikan bila dipilih eksplisit. Review synthetic dan stream synthetic yang lama dipertahankan.

**BATAS:** Belum ada mitra atau replay berizin yang dikonfirmasi. Fixtures BE-04 seluruhnya authored synthetic. Tidak mencakup geometri/rule body baru, inferensi provider, UI, source live, domain review, atau validasi operasional.

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

1. Import multipart memvalidasi file bytes lewat `ReplayImportService`; conflict menjadi 409 dan invalid input 422.
2. `replay-source`, `replay-frame`, dan `evidence` menggunakan public SQLite reader; frame source-only dibangun dari `ArchiveReplayEventSource` + `ObservedStateReducer`, tanpa detector rerun. Derived `predictions`/`alerts` null jika analysis tidak dipilih atau frame tidak tersedia.
3. Imported review membaca source immutable dan hanya menerima kontrol playback yang diizinkan `Review.execute`; branch dan simulator commands ditolak. Private checkpoint tidak dibaca.
4. Create imported review mengembalikan `source_read_token` 8 jam yang terikat source dan role actor. Credential read-only ditolak oleh route control/write.
5. Event paging memakai ordinal stabil. Cutoff time diterapkan sebelum paging untuk import dan synthetic archive; cursor tidak melewatkan event dengan timestamp yang sama. Synthetic WebSocket first-message auth dan payload snapshot tidak diubah.

## 6. Output yang harus diserahkan

Scoped REST/review reads dan main stream compatibility untuk FE adapter; unresolved evidence response eksplisit, bukan fabricated event.

## 7. Asumsi dan unknown

**ASSUMPTION:** Evaluator baseline menggunakan instructor replay capability, enum Role current dipertahankan.

**UNKNOWN:** Identity policy organisasi mitra tidak dibutuhkan untuk scoped synthetic seats. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

`tests/integration/test_be_04.py` memakai TestClient, temporary SQLite, fake wall/monotonic clock, operator test token, dan data replay authored synthetic. Pemeriksaan 4 Oktober 2026:

| Test/check | Command | Hasil aktual |
|---|---|---|
| API import/retry/conflict/invalid input, source/frame/event paging, evidence, token scope/expiry, imported review read-only, synthetic compatibility | `python -m pytest tests/integration/test_be_04.py` | Lulus, 5 tests; runtime TestClient saja. |
| Ruff pada seluruh file source/test berubah | `python -m ruff check --ignore B008,UP041 backend/app.py backend/review.py tests/integration/test_be_04.py` | Lulus. Pengecualian FastAPI `Depends` dan `asyncio.TimeoutError` mengikuti pola legacy yang sudah dicatat di inventaris BE-01. |
| Scoped type check | `python -m mypy --follow-imports=skip backend/app.py backend/review.py tests/integration/test_be_04.py` | Lulus untuk tiga file yang diperiksa; imported modules dilewati. |
| Patch whitespace | `git diff --check` | Exit 0; Git memberi peringatan konversi LF→CRLF pada `app.py` dan `review.py`. |

Pemeriksaan tambahan:

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Ruff tanpa pengecualian | Semua file source/test berubah | `python -m ruff check backend/app.py backend/review.py tests/integration/test_be_04.py` | Belum bersih: temuan `B008` untuk pola `Depends(...)` FastAPI dan `UP041` pada timeout handling legacy di `app.py`; scoped check di atas lulus dengan dua kode ini dikecualikan. |
| Reconnect/UI | FE-02 API adapter + BE archive | `python -m pytest tests/browser/test_api_reconnect.py` | Tidak dijalankan pada task ini. |

Hasil TestClient tidak membuktikan startup/deployment server atau integrasi browser/provider. Task memenuhi kriteria API scoped pada harness ini; fidelity source mitra, review pakar domain, dan validasi operasional belum tercapai.
