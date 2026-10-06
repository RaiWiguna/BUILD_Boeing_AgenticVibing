# BE-07 — Append-only transcript review dan debrief exports

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** Implementasi source dan pemeriksaan terpilih lulus, 5 Oktober 2026. Belum ada domain review atau validasi operasional.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyimpan koreksi/decision reviewer sebagai revision terpisah yang durable dan menghasilkan debrief dengan source/result/uncertainty yang dapat ditelusuri.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (sebelum BE-07):** `Review.annotations` dan review command receipts synthetic in-memory; reporting.py memiliki export synthetic tetapi belum mempunyai transcript revision/assist debrief.

**DELIVERED (BE-07):** Imported replay sekarang memiliki correction/review receipts, transcript revision dan annotation append-only, review history pada read model/snapshot, typed `review_annotation` stream, serta read-only debrief JSON/CSV/HTML. Report synthetic `/report` tetap dipisahkan. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/reporting.py](../../../../backend/reporting.py)
- [backend/review.py](../../../../backend/review.py)
- [backend/models.py](../../../../backend/models.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §14.2–14.6, §13.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/app.py`, `backend/review.py`, `backend/reporting.py`

**File baru usulan, belum ada:** Tidak ada file source baru di task ini.

**File usulan dari task lain yang diperluas, belum ada:** `backend/assist_service.py`, `backend/assist_storage.py`

Mengubah assist_service/storage yang diperkenalkan BE-05; reviewer/time dari token/server, tidak dari provider/client bebas. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. BE-06→BE-07→BE-08 untuk shared BE files.

## 4. Kontrak dan dependency

**Contract:** SC-05/06 dan C-05/C-08. SC-05 ReviewAnnotation + SC-06 correction/review request; C-05 analysis revision binding dan C-08 receipts. Consumer FE-05 dan QA.

**Implementation dependency:** [BE-06](../backend/BE-06-assist-result-evidence-stream.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Raw/corrected pair, same request retry/stale expected revision dan FakeReportReader; annotations ke source time, bukan review wall time.

**Integration dependency:** BE-03/06 storage, FE-05 UI correction/export dan QA-03/05.

## 5. Pendekatan implementasi

1. Revision/annotation source- dan analysis-bound memeriksa target dan expected revision sebelum menulis; receipt terikat request id, body, dan actor server.
2. Correction membuat revision baru; raw ASR, candidate text, source event, clearance, alert, severity, dan worker result tetap immutable.
3. Receipt, annotation/revision, dan assist sequence tersimpan dalam satu transaksi `Archive.db`. Migrasi additive memperluas CHECK stream BE-06 sambil mempertahankan baris lama.
4. Read model/snapshot menampilkan raw transcript, corrected view, annotation history, decision terkini, uncertainty, dan provenance. Reconnect tetap mengirim full authorized snapshot.
5. Endpoint `/debrief` mengekspor imported replay secara read-only. JSON/CSV/HTML tidak mengambil restricted truth atau data audio privat; HTML di-escape dan CSV melindungi formula setelah whitespace/control prefix.

## 6. Output yang harus diserahkan

Durable review/correction service dan debrief exports untuk FE tersedia di source. SQLite sementara menunjukkan raw result dan source tetap sama serta revisions/receipts/annotations/sequence terbaca kembali sesudah reopen.

## 7. Asumsi dan unknown

**ASSUMPTION:** Review target version hanya bertambah pada accepted append; archive sumber tidak diedit.

**UNKNOWN:** Rubrik domain/advisory relevance mitra belum tersedia, tidak diisi otomatis. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

Pemeriksaan berikut dijalankan pada 5 Oktober 2026. Fixture transcript, candidate, replay, dan WAV dibuat sintetik untuk TestClient; tidak ada provider inference atau data runtime/mitra.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| BE-06 compatibility + review/restart | Authored synthetic transcript/candidate, temporary SQLite, fake clock | `python -m pytest tests/integration/test_be_06.py tests/integration/test_be_07.py` | Lulus, 30 tests; raw source/worker result immutable, durable corrected view/history/receipt/sequence survive reopen, dan BE-06 rows survive stream schema migration. |
| Negative/idempotency/scope/stream | Stale revision, request id reused with changed body/actor, source-read token, reconnect | Command sama | Lulus: 409/403/404/422 sesuai kasus tanpa partial append; retry identik receipt sama; annotation sequence bertambah sekali dan message typed. |
| Debrief/export | Synthetic provenance, alignment unknown, HTML/formula text | Command sama | Lulus: JSON/CSV/HTML mempertahankan provenance/uncertainty, formula/HTML aman, tanpa audio path/token/restricted truth. |
| Ruff | BE-06/07 scoped files; pengecualian FastAPI/timeout legacy | `python -m ruff check --ignore B008,UP041 backend/app.py backend/review.py backend/reporting.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py tests/integration/test_be_07.py` | Lulus. |
| Mypy | Tujuh scoped source/test files | `python -m mypy --follow-imports=skip backend/app.py backend/review.py backend/reporting.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py tests/integration/test_be_07.py` | Lulus; imported modules dilewati sesuai opsi. |
| Diff whitespace | Working tree | `git diff --check` | Exit 0; Git memberi notifikasi line-ending LF→CRLF pada empat file backend. |

Integration checks yang belum dijalankan:

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Browser review | FE-05 correction→refresh→export | `python -m pytest tests/browser/test_review_debrief.py` | Accepted revision tampil setelah server commit; source hash/clearance/alert severity tetap. |

Hasil di atas membuktikan source dan runtime dalam harness TestClient/SQLite sementara. Tidak ada build, deployment, browser suite, provider/ASR inference, AI-02 process isolation, domain review, validasi mitra, atau validasi operasional.
