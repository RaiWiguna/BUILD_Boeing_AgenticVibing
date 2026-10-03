# BE-06 — Assist result commit, evidence reads, dan stream

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyimpan hasil worker valid tepat satu kali dan menyajikan transcript/highlight/option sesuai source, analysis window, role dan replay time.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Belum ada assist result schema/storage/routes; event history current adalah dict dan report instructor mengandung truth sehingga tidak boleh menjadi model evidence input.

**TARGET:** Result sink/schema integrity, source/version analysis binding, typed assist subscriptions dan evaluator-only options. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.2, §10.4, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/app.py`

**File baru usulan, belum ada:** Tidak ada file source baru di task ini.

**File usulan dari task lain yang diperluas, belum ada:** `backend/assist_service.py`, `backend/assist_storage.py`

Mengubah file baru yang diperkenalkan BE-05 (`assist_service.py/assist_storage.py`) saja selain app; model DTO/reconciliation milik AI. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. BE-05→BE-06→BE-07 untuk app/assist_service/assist_storage.

## 4. Kontrak dan dependency

**Contract:** SC-02/04/05/06 dan C-02/C-05/C-07. SC-04 WorkerResult→SC-05 entities/highlights/options; SC-06 assist-stream union; C-02/05/07 validation/window/cursor rules. Consumer FE-02/05.

**Implementation dependency:** [BE-05](../backend/BE-05-private-audio-job-dispatch.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** WorkerResult valid/invalid fixtures, InMemoryEvidenceReader dan source events tanpa truth; cancelled attempt fixture.

**Integration dependency:** AI-02–05 results, BE-03 source persistence dan FE-05 candidate/evidence review.

## 5. Pendekatan implementasi

1. Validate job/attempt/asset/input hash/model versions sebelum payload; hanya current running attempt boleh commit.
2. Resolve typed evidence refs pada source+analysis window yang sama; reject foreign/dangling refs/extra action fields; transcript unresolved alignment tetap diberi uncertainty.
3. Commit accepted result batch+terminal job state+assist sequence atomik. Duplicate valid attempt mengembalikan receipt; payload berubah conflict.
4. Expose transcripts/highlights/options/job reads dari stored DTO; opsi hanya instructor evaluator replay capability. Jangan gabungkan detector severity dengan review_priority.
5. Assist-stream mengirim snapshot union C-07 lalu ordered updates; time filtering berdasarkan evidence availability, snapshot reconnect resync; source WS/read tetap tersedia ketika assist gagal.

## 6. Output yang harus diserahkan

Durable analysis results, scoped EvidenceReader dan assist REST/WS untuk FE; tidak ada option execute endpoint.

## 7. Asumsi dan unknown

**ASSUMPTION:** Analysis results versioned immutable; server schema validator terpisah dari provider validator.

**UNKNOWN:** Makna factual support/relevance perlu evaluasi corpus/domain, bukan disimpulkan dari valid JSON. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 memiliki result/stream assertions dengan fixed DTO fixtures. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Commit | Valid attempt + F-COMM-01 refs | `python -m pytest tests/integration/test_be_06.py` | Satu batch/receipt; source/model/input versions dan refs utuh setelah reopen. |
| Negative | Dangling/foreign evidence, late/cancelled attempt, action field | Command sama | Result ditolak tanpa partial segments/options; source read tidak rusak. |
| Contract | Assist snapshot/sequence gap dan earlier until_ms | Command sama | No future evidence/candidate leak; source sequence berbeda dari assist sequence. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Assist UI | AI stub/real result + FE-02/05 | `python -m pytest tests/browser/test_assist_stream.py` | Option muncul hanya pada evaluator replay dan refs membuka evidence yang tepat. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
