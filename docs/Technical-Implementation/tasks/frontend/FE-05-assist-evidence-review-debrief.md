# FE-05 — Transcript, candidate evidence review, dan debrief

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status (6 Oktober 2026):** UI/read-model dan fixture FE-05 tersedia di source; `npm run typecheck` dan `npm run build` lulus. API assist/transcript/evidence/audio tetap unavailable karena route/capability backend belum tersedia. Runtime, browser QA, domain review, dan validasi operasional belum diverifikasi.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memberi evaluator UI untuk inspeksi transcript/highlights/options, koreksi/decision dan debrief dengan provenance serta uncertainty.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE, 6 Oktober 2026:** FE-05 menambahkan transcript provenance/revision panel, evaluator-only highlight/options panel, generic correction/review editor, dan debrief. Port/read models membawa typed evidence refs, nullable revisions/confidence, provenance, serta audio/session alignment state. Fixture conflict adalah simulasi lokal authored; bukan receipt server.

**Batas belum terintegrasi:** API adapter mengembalikan unavailable untuk assist ketika profile/routes tidak aktif; tidak menggunakan report instructor/truth untuk debrief. Backend belum menyediakan `source_read` terpisah atau transcript/highlight/option review/evidence/audio route. Tidak ada provider, persistence FE-05, atau export FE-05 yang diklaim.

## 3. Context dan ownership

- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [backend/app.py](../../../../backend/app.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §12.3–12.4, §14.5.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**File source baru:** `frontend/src/features/assist/TranscriptPanel.tsx`, `frontend/src/features/assist/CandidatePanel.tsx`, `frontend/src/features/assist/ReviewEditor.tsx`, `frontend/src/features/assist/DebriefPanel.tsx`.

**File existing yang diperluas:** `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/src/contracts/replayReview.ts`, `frontend/src/contracts/apiWire.ts`, `frontend/src/adapters/apiDecoders.ts`, `frontend/src/adapters/apiReplayReview.ts`, `frontend/src/adapters/fixtureReplayReview.ts`, `frontend/src/features/replay/ReplayController.ts`, `frontend/src/features/replay/ReplayTimeline.tsx`, `frontend/src/features/replay/AudioPlayer.tsx`, `frontend/src/features/runway/AlertEvidence.tsx`, `frontend/src/vite-env.d.ts`.

No buttons execute/send-clearance; feature controllers call adapter only. Reviewer confirm/dismiss adalah evaluasi candidate, bukan authority operasi. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/styles sesudah FE-04; api adapter FE-02 tetap file terpisah.

## 4. Kontrak dan dependency

**Contract:** SC-05/06/07 dan C-02–C-05/C-07/C-08. Segments/revisions/highlights/options/evidence/capabilities/job state→review/debrief; correction and review requests idempotent via adapter.

**Implementation dependency:** [FE-01](../frontend/FE-01-typed-fixture-adapter-scaffold.md), [FE-03](../frontend/FE-03-source-context-runway-map.md), [FE-04](../frontend/FE-04-replay-timeline-audio-controls.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Fixture:** Raw/corrected authored pair, `linked`/`possible_link`, typed refs, evaluator/training view (`VITE_FLOWLENS_FIXTURE_VIEW`), AI unavailable notice, and a local conflict→refresh→explicit retry example. Fixture annotation receipts are in-memory only; no ASR/provider/server result/partner data is represented.

**Integration dependency:** FE-02 API + BE-06/07 persisted results/revisions; AI real quality bukan UI pass.

## 5. Pendekatan implementasi

1. Source text/revision, provenance, channel/speaker/confidence nullable fields, audio-relative timebase and unknown alignment are shown separately.
2. Highlights/options use typed refs; `linked`, `possible_link`, `unresolved`, and `unavailable` remain distinct. Selecting a resolved source ref loads read-only frame context through the adapter; audio-relative selection does not claim session alignment or send a replay command.
3. Options/highlights appear only when evaluator capability is granted. No command, clearance, severity, alert, or lifecycle callback exists.
4. Corrections and candidate decisions carry expected revision and request ID through the adapter. Conflict retains the draft; refresh/reconcile and explicit retry are separate actions. Fixture acceptance is labeled local memory only.
5. Debrief separates source events/alerts, candidates, unknowns, and reviewer annotations; versions, analysis window, and usage limits are visible. Restricted truth report is not consumed or exported.

## 6. Output yang harus diserahkan

Assist/reviewer/debrief components wired to typed port/read models and explicit fixture/API behavior. Fixture revisions/history are authored and in-memory; server append-only persistence is unverified and currently unavailable.

## 7. Asumsi dan unknown

**ASSUMPTION:** Instructor-scoped evaluator capability from server, not dropdown; synthetic quality visibly unvalidated.

**UNKNOWN:** Reviewer ATCO protocol/domain relevance and real ASR accuracy. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

Pemeriksaan aktual 6 Oktober 2026 dari `frontend/`:

- `npm run typecheck` — lulus.
- `npm run build` — lulus; Vite menghasilkan bundle lokal.
- Automated QA/browser test tidak dijalankan; namespace `tests/` tidak diubah. Runtime API/browser, domain review, dan validasi operasional tidak diverifikasi.

QA-05 owns browser workflow and no-command assertions. Command berikut tetap TARGET dan tidak dijalankan:

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

Source/build criteria §6 terpenuhi untuk fixture UI; browser assertions dan API persistence/integration tetap pending. Typecheck/build bukan bukti runtime, QA browser, domain fidelity, atau validasi operasional.
