# FE-03 — Source context, runway map, dan deterministic evidence

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status:** Source FE-03 tersedia di `feat/frontend`; `npm run typecheck` dan `npm run build` lulus pada 5 Oktober 2026. Runtime/browser QA, domain review, dan validasi operasional belum dilakukan.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menampilkan public runway geometry, observed/last-known tracks dan predicted occupancy dengan label waktu/kualitas serta evidence yang jelas.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE, 5 Oktober 2026:** FE-01/FE-02 adapter/read models kini dipakai oleh dashboard source context. Map SVG, runway board, dan deterministic alert evidence panel tersedia di source FE. Fixture adapter menyediakan authored `LOCAL_METRES` layout, observed/last-known tracks, prediction, alert, acknowledgement, dan event refs yang resolve dalam fixture scope.

**CURRENT_SOURCE, API boundary:** `ApiReplayReviewAdapter` tetap memerlukan credential `source_read`. Backend saat ini tidak menerbitkan credential terpisah dan tidak memiliki route historical frame-at-time atau route evidence/assist additive. API mode menampilkan unauthorized/unavailable sesuai akses adapter; operator token tidak dipasang sebagai `source_read`, dan tidak ada fixture fallback.

**TARGET:** Source setup/header, SVG map/runway board dan deterministic alert evidence panels. Tidak mengimplementasikan detector/provider/database atau memberi opsi AI jalur command.

## 3. Context dan ownership

- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [backend/detection.py](../../../../backend/detection.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.3–7.4, §10.4, §12.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang diubah:** `frontend/src/contracts/replayReview.ts`, `frontend/src/adapters/apiDecoders.ts`, `frontend/src/adapters/fixtureReplayReview.ts`, `frontend/src/App.tsx`, dan `frontend/src/styles.css`.

**File baru yang tersedia:** `frontend/src/features/runway/RunwayMap.tsx`, `frontend/src/features/runway/RunwayBoard.tsx`, `frontend/src/features/runway/AlertEvidence.tsx`, `frontend/src/features/replay/SourceSetup.tsx`.

**File existing yang diperluas FE-03:** `frontend/src/App.tsx`, `frontend/src/styles.css`.

No severity/occupancy recomputation di UI; metrics/result server rendered with calculation time/source IDs. API unavailable dapat memakai fixture adapter explicit. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/styles setelah FE-01 dan sebelum FE-04.

## 4. Kontrak dan dependency

**Contract:** SC-02/05/06/07. SC-07 source/frame/layout/quality/deterministic alert models→SVG/details; source selection passes stable ID to adapter; consumer FE-04/05 evidence selection.

**Implementation dependency:** [FE-01](../frontend/FE-01-typed-fixture-adapter-scaffold.md) dan FE-02 menyediakan adapter/read model yang dipakai. Data layout/track/prediction/alert runtime riil memerlukan snapshot API yang accessible dengan scope benar; historical API frame dan source-read credential belum tersedia di backend.

**Mock/stub:** Valid LOCAL_METRES baseline, mirrored/rotated display and unknown/degraded fixtures; StubEvidenceReader returns exact refs.

**Integration dependency:** FE-02 real adapter dan BE/SD public frames.

## 5. Pendekatan implementasi

1. Source panel merender jenis/label/provenance/version/quality, versi layout, waktu frame dan koneksi; coverage, readiness model dan role diberi status “not exposed” ketika read model tidak menyediakannya.
2. SVG memproyeksikan runway, protected area, taxiway, hold line, footprint dan declared route yang memang ada pada layout/read model `LOCAL_METRES`. Arah 09/27 ditampilkan dari mapping layout bersama orientasi sumbu lokal; tidak memberi bearing utara.
3. Observed dan last-known dibedakan lewat outline/bentuk dan label teks. Waktu sample, receive, frame dan playback tampil dengan label terpisah. Prediction tetap berupa relative seconds; `exit_unknown` selalu terlihat dan tidak menjadi klaim runway clear.
4. Runway board dan alert panel merender state, quality, occupants, predictions, dimensions, lifecycle, severity, metrics, ages, assumptions, evidence IDs serta acknowledgement secara terpisah dari read model; UI tidak menjalankan detector.
5. Evidence event diselesaikan lewat adapter berdasarkan ID, source scope dan cutoff waktu. Missing/unavailable lookup tetap ditandai; UI tidak membuat event dari alert reason. Disconnected frame terakhir dapat dipertahankan berlabel tanpa extrapolation.
6. Loading/empty/error/degraded/unauthorized/unsupported-layout states disajikan pada panel yang sesuai. Tidak ada pilihan live feed/audio, command AI, atau rekomendasi untuk posisi aktif.

## 6. Output yang harus diserahkan

Runway/map/source context components usable via fixture port, wired App and styles. Source-level behavior ready for FE timeline integration. `npm run typecheck` dan `npm run build` lulus pada 5 Oktober 2026. QA browser criteria pada §8 belum dijalankan oleh task FE.

## 7. Asumsi dan unknown

**ASSUMPTION:** Baseline small object count fits SVG; local axes are explicitly `LOCAL_METRES` and are not labeled WGS84.

**UNKNOWN:** Site layout and actual display/human-factors review. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-05 owns visual/behavior browser tests; screenshot not numerical oracle. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Browser | Synthetic frames+layout+alert evidence | `python -m pytest tests/browser/test_fe_03.py` | Rendered body/time/resource/labels match fixture; evidence links resolve exact refs. |
| Degraded | Missing/stale/unknown exit/unsupported layout | Command sama | Unknown/last-known visible, no runway-clear claim or synthetic layout fallback. |
| Accessibility | Keyboard/focus/text labels/narrow viewport | Command sama | Controls/details usable; no clipping or reliance on color only. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Observed/predicted parity | BE+SD frame via FE-02 | `python -m pytest tests/browser/test_runway_evidence.py` | Displayed values/time/version match archived result; frontend tidak recalculate severity. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.

### Verifikasi aktual FE-03, 5 Oktober 2026

- Dari `frontend/`, `npm run typecheck` — exit code 0.
- Dari `frontend/`, `npm run build` — exit code 0; Vite menghasilkan `dist/index.html` dan asset lokal.
- Browser/QA, API/WS runtime, trainer/domain review dan validasi operasional — tidak dijalankan.
