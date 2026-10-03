# BE-07 — Append-only transcript review dan debrief exports

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyimpan koreksi/decision reviewer sebagai revision terpisah yang durable dan menghasilkan debrief dengan source/result/uncertainty yang dapat ditelusuri.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Review.annotations dan review command receipts in-memory; reporting.py meng-escape HTML/CSV tetapi belum mempunyai transcript revision/assist summaries.

**TARGET:** Correction/review receipts, persisted annotations dan read-only debrief JSON/CSV/HTML. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

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

1. Implement per-target revision dan idempotent request_id+body+actor receipts; validate role/target/source/expected revision sebelum append.
2. Correction membuat new revision tanpa overwrite raw ASR; confirm/dismiss/unresolved tidak mengubah recorded clearance/alert severity.
3. Persist transcript revisions/annotations source-linked; new analysis menunjuk selected transcript revisions dan mempertahankan raw/model version.
4. Extend existing report atau additive debrief projection dengan factual events, candidate statements, unknowns, reviewer revisions, valid evidence links dan synthetic/authorized limits.
5. Pertahankan instructor restricted truth export terpisah dari public debrief/model input; escape HTML, formula-safe CSV, tanpa tokens/private audio paths.

## 6. Output yang harus diserahkan

Durable review/correction service dan debrief exports untuk FE; restart mempertahankan raw result serta history annotations.

## 7. Asumsi dan unknown

**ASSUMPTION:** Review target version hanya bertambah pada accepted append; archive sumber tidak diedit.

**UNKNOWN:** Rubrik domain/advisory relevance mitra belum tersedia, tidak diisi otomatis. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 memiliki persistence/idempotency/export tests. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Review | F-REVIEW-01 valid correction+reopen | `python -m pytest tests/integration/test_be_07.py` | Raw text tidak berubah; corrected version/reviewer/reason survive restart. |
| Negative | Stale revision, reused ID changed payload/actor | Command sama | 409 tanpa append baru; same ID identik mengembalikan receipt lama. |
| Export | Injected HTML/formula text dan unknown refs | Command sama | Output aman di-render/parse, uncertainty terlihat, tidak memuat secrets/truth pada public view. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Browser review | FE-05 correction→refresh→export | `python -m pytest tests/browser/test_review_debrief.py` | Accepted revision tampil setelah server commit; source hash/clearance/alert severity tetap. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
