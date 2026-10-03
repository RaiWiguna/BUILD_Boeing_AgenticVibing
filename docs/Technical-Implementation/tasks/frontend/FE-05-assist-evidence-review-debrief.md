# FE-05 — Transcript, candidate evidence review, dan debrief

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memberi evaluator UI untuk inspeksi transcript/highlights/options, koreksi/decision dan debrief dengan provenance serta uncertainty.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Tidak ditemukan transcript/candidate/review UI; existing TS Assessment berbeda dari durable transcript correction contract.

**TARGET:** Raw/corrected transcript, linked/possible_link evidence, evaluator-only options, revision-conflict and debrief/export views. Tidak mengimplementasikan detector/provider/database atau memberi opsi AI jalur command.

## 3. Context dan ownership

- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [backend/app.py](../../../../backend/app.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §12.3–12.4, §14.5.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `frontend/src/features/assist/TranscriptPanel.tsx`, `frontend/src/features/assist/CandidatePanel.tsx`, `frontend/src/features/assist/ReviewEditor.tsx`, `frontend/src/features/assist/DebriefPanel.tsx`

**File usulan dari task lain yang diperluas, belum ada:** `frontend/src/App.tsx`, `frontend/src/styles.css`

No buttons execute/send-clearance; feature controllers call adapter only. Reviewer confirm/dismiss adalah evaluasi candidate, bukan authority operasi. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/styles sesudah FE-04; api adapter FE-02 tetap file terpisah.

## 4. Kontrak dan dependency

**Contract:** SC-05/06/07 dan C-02–C-05/C-07/C-08. Segments/revisions/highlights/options/evidence/capabilities/job state→review/debrief; correction and review requests idempotent via adapter.

**Implementation dependency:** [FE-01](../frontend/FE-01-typed-fixture-adapter-scaffold.md), [FE-03](../frontend/FE-03-source-context-runway-map.md), [FE-04](../frontend/FE-04-replay-timeline-audio-controls.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** F-COMM-01/raw-corrected pair/linked vs possible_link, evaluator and training seat fixtures, 409 response and AI unavailable.

**Integration dependency:** FE-02 API + BE-06/07 persisted results/revisions; AI real quality bukan UI pass.

## 5. Pendekatan implementasi

1. Render raw ASR/corrected revision distinction, speaker/confidence unknowns, timestamps and source/model/rule versions; no false final transcript authority.
2. Attach highlight to existing deterministic alert evidence panel when linked; possible_link explicit, no duplicate hazard card or severity alteration.
3. Evaluator-only options show rationale/preconditions/unknowns/refs and analysis window; evidence selection updates timeline/audio using port, no command callback.
4. Corrections/confirm/dismiss/unresolved pending state only accepted after server receipt; 409 preserves draft and refreshes revision, rejected requests not success.
5. Debrief separates source facts/candidates/unknowns/reviewer annotations and restricted truth access; export labels/limits visible. AI outage panel degraded while replay usable.

## 6. Output yang harus diserahkan

Assist/reviewer/debrief components wired to typed port and eventual API, with append-only revision/history presentation.

## 7. Asumsi dan unknown

**ASSUMPTION:** Instructor-scoped evaluator capability from server, not dropdown; synthetic quality visibly unvalidated.

**UNKNOWN:** Reviewer ATCO protocol/domain relevance and real ASR accuracy. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-05 owns browser workflow and no-command assertions. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Browser | Valid linked highlight/option/raw-corrected fixture | `python -m pytest tests/browser/test_fe_05.py` | Refs open exact evidence, raw/corrected traceable; options only evaluator replay. |
| Negative | Foreign/unresolved evidence/401/409/AI outage | Command sama | No fabricated facts/success; draft conflict preserved; source playback usable. |
| Boundary | Option text with imperative words | Command sama | Zero command network requests and no execute control; severity/lifecycle unchanged. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Review persistence | BE-07 correction→refresh/restart→debrief | `python -m pytest tests/browser/test_review_debrief.py` | Raw ASR preserved, accepted annotations persist and exports source/model/review provenance. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
