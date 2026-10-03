# FE-04 — Replay timeline, audio alignment, dan controls

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyelaraskan map/event/clearance/transcript lanes pada selected replay time dan menyediakan playback/seek yang menunjukkan actual frame time.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Review supports START/PAUSE/SET_SPEED/SEEK; snapshot events tail non-TRACK sehingga history lengkap perlu cursor API; belum ada timeline/player.

**TARGET:** Timeline/controller/audio playback controls with unknown alignment and concurrency/disconnect states. Tidak mengimplementasikan detector/provider/database atau memberi opsi AI jalur command.

## 3. Context dan ownership

- [backend/review.py](../../../../backend/review.py)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.5, §12.2–12.4, §13.6, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `frontend/src/features/replay/ReplayTimeline.tsx`, `frontend/src/features/replay/ReplayControls.tsx`, `frontend/src/features/replay/ReplayController.ts`, `frontend/src/features/replay/AudioPlayer.tsx`

**File usulan dari task lain yang diperluas, belum ada:** `frontend/src/App.tsx`, `frontend/src/styles.css`

FE controls review only; server/adapter owns revision/receipt/cursor. No commands derived from audio/AI. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/styles setelah FE-03 dan sebelum FE-05.

## 4. Kontrak dan dependency

**Contract:** SC-02/05/06/07. SC-07 frame/events/transcript/controls/audio read; C-02 actual vs requested time, C-03 receive causality, C-04 scoped audio; selected evidence feeds FE-05.

**Implementation dependency:** [FE-01](../frontend/FE-01-typed-fixture-adapter-scaffold.md), [FE-03](../frontend/FE-03-source-context-runway-map.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** FixtureReviewAdapter clock and full event pagination; synthetic WAV optional, transcript-only audio unavailable explicitly.

**Integration dependency:** FE-02 transport + BE-04 review/BE-05 audio; QA browser.

## 5. Pendekatan implementasi

1. Timeline lanes source communication/structured clearance/TRACK/alert/transcript/reviewer separated; order available receive time+ordinal.
2. Load full cursor history rather than snapshot tail; seek recomputes view by archive frame <= target and event cutoff. Display frame_ms and playback/requested_ms separately.
3. Expose START/PAUSE and supported speeds; preserve expected revision/request identity; pending controls disabled duplicate submit, conflict refresh/reconcile.
4. Audio uses asset-relative seek mapping C-03/04; alignment unknown allows unaligned playback with label, no fake synced transcript. Revoke object URL on cleanup.
5. On disconnect retain last frame with stale/disconnected badge; no fresh extrapolation; independent assist failure must not stop source playback.

## 6. Output yang harus diserahkan

Timeline/controller/audio components and consistent selected-time/evidence context for FE-05 and QA browser.

## 7. Asumsi dan unknown

**ASSUMPTION:** Visual interpolation optional and labeled; baseline uses exact recorded frames without inferred observations.

**UNKNOWN:** Codec/browser/time drift compatibility actual audio. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-05 owns seek/time/audio UI assertions. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Timeline | Frames 200/400 ms, target 350; same-time ordinals | `python -m pytest tests/browser/test_fe_04.py` | Frame 200 displayed as actual time; no events after cutoff; lane/order correct. |
| Negative | Unknown alignment/no audio/conflict/disconnect | Command sama | Separate labels and recovery; no fabricated audio success or future observation. |
| Controls | Pause/start/speed/seek retry via fixture | Command sama | Simulation aging freezes on pause; ms/seconds mapping correct and one accepted effect. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Real replay/audio | BE review+private audio via FE-02 | `python -m pytest tests/browser/test_replay_audio.py` | Same source time context map/timeline/audio; wrong source playback denied and source immutable. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
