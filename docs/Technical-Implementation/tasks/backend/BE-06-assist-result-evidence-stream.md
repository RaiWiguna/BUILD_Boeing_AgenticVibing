# BE-06 — Assist result commit, evidence reads, dan stream

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** Implemented in BE-owned source; selected integration checks passed 4 Oktober 2026. This records source and test-harness status only.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyimpan hasil worker valid tepat satu kali dan menyajikan transcript/highlight/option sesuai source, analysis window, role dan replay time.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE after BE-06:** `assist_service.py` defines a local extra-forbid SC-04/05 result adapter; `assist_storage.py` appends immutable analysis/result/receipt/stream rows through the existing `Archive.db` connection; `app.py` adds transcript, highlight, evaluator-only option reads, assist snapshot, evidence-segment resolution, and `/assist-stream`. Source event history remains the BE-04 archive projection. Instructor reports contain restricted truth and are not used as model evidence.

**Implementation boundary:** AI-01's DTO package and AI-02's process worker are not available, so the BE-local DTO/adapter follows SC-04/05. The fixed WorkerResult fixture used by integration checks is explicitly synthetic. No transcript/highlight/option is generated from fixture audio. This is not provider/ASR inference, AI-02 process isolation, domain review, partner-data validation, deployment, or operational validation.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.2, §10.4, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/app.py`

**File baru ditambahkan:** `tests/integration/test_be_06.py`, authorized by the BE-06 implementation request for scoped producer assertions.

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
5. `assist-stream` authenticates its first message, emits a typed `assist-1` snapshot and ordered updates, keeps assist sequence separate from source sequence, and resyncs with a scoped snapshot on gaps or filtered updates. The existing synthetic source WebSocket remains compatible.

## 6. Implemented output

Durable assist analysis/result rows, version metadata, immutable receipt, stream sequence/events, scoped transcript/highlight reads, evaluator-only options, transcript evidence resolution, and typed assist REST/WS reads are present in source. No option execute endpoint exists. Analysis windows and result availability are applied before historical paging; unknown alignment is marked and excluded from historical-time reads. `review_priority` remains an assist field and is not merged with detector severity.

## 7. Asumsi dan unknown

**ASSUMPTION:** Analysis results are versioned immutable; server schema validation is separate from any provider validation. Until AI-01 exists, the local strict adapter is temporary BE-owned glue.

**UNKNOWN:** Makna factual support/relevance perlu evaluasi corpus/domain, bukan disimpulkan dari valid JSON. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

`tests/integration/test_be_06.py` holds the focused result/stream assertions with fixed synthetic DTO fixtures.

Tests mandiri (dependency AI memakai fixture sintetik):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Commit | Fixed synthetic WorkerResult + same-source event/segment refs | `python -m pytest tests/integration/test_be_06.py` | Passed, 24 tests; result batch, terminal job state, analysis, receipt, and assist sequence reopen from temporary SQLite. |
| Negative | Foreign/dangling evidence, hash/source/version/job/attempt mismatch, action fields, timeout/cancel/stale attempt | Command sama | Passed; no partial result rows or source mutation. |
| Contract | Source/read-token scope, evaluator-only options, historical cutoff, typed snapshot/reconnect, ordered updates and gap | Command sama | Passed; future result rows stay hidden at earlier replay time; assist sequence is separate from source WebSocket payload. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Assist UI | AI stub/real result + FE-02/05 | `python -m pytest tests/browser/test_assist_stream.py` | Option muncul hanya pada evaluator replay dan refs membuka evidence yang tepat. |

Verification actually run on 4 October 2026:

- `python -m pytest tests/integration/test_be_06.py` — passed, 24 tests, using `TestClient`, temporary SQLite, fake clocks, and fixed synthetic worker results.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py` — passed.
- `python -m mypy --follow-imports=skip backend/app.py backend/assist_service.py backend/assist_storage.py tests/integration/test_be_06.py` — passed; imported modules were skipped.
- `git diff --check` — passed; Git printed CRLF conversion notices for the three edited backend files.

These checks cover the stubbed technical path only. They do not verify AI-02 process isolation, provider inference/ASR, browser integration, domain review, partner data, build/deployment, or operational validity.
