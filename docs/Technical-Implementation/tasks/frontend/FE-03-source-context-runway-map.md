# FE-03 — Source context, runway map, dan deterministic evidence

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menampilkan public runway geometry, observed/last-known tracks dan predicted occupancy dengan label waktu/kualitas serta evidence yang jelas.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Belum ada dashboard/map; source provides layout/snapshot tracks/predictions/runway and typed TS subset.

**TARGET:** Source setup/header, SVG map/runway board dan deterministic alert evidence panels. Tidak mengimplementasikan detector/provider/database atau memberi opsi AI jalur command.

## 3. Context dan ownership

- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [backend/detection.py](../../../../backend/detection.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.3–7.4, §10.4, §12.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `frontend/src/features/runway/RunwayMap.tsx`, `frontend/src/features/runway/RunwayBoard.tsx`, `frontend/src/features/runway/AlertEvidence.tsx`, `frontend/src/features/replay/SourceSetup.tsx`

**File usulan dari task lain yang diperluas, belum ada:** `frontend/src/App.tsx`, `frontend/src/styles.css`

No severity/occupancy recomputation di UI; metrics/result server rendered with calculation time/source IDs. API unavailable dapat memakai fixture adapter explicit. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/styles setelah FE-01 dan sebelum FE-04.

## 4. Kontrak dan dependency

**Contract:** SC-02/05/06/07. SC-07 source/frame/layout/quality/deterministic alert models→SVG/details; source selection passes stable ID to adapter; consumer FE-04/05 evidence selection.

**Implementation dependency:** [FE-01](../frontend/FE-01-typed-fixture-adapter-scaffold.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Valid LOCAL_METRES baseline, mirrored/rotated display and unknown/degraded fixtures; StubEvidenceReader returns exact refs.

**Integration dependency:** FE-02 real adapter dan BE/SD public frames.

## 5. Pendekatan implementasi

1. Render source kind/synthetic-or-authorized label, versions/coverage/model readiness/role/connection prominently; no live-connect choices.
2. Map local metres with explicit axes/direction; show physical 09/27 shared resource, footprint dimensions, known route and hold/protection geometry.
3. Distinguish observed/last-known and predictions by shape/text/time, not color alone; exit_unknown not definite runway-clear estimate.
4. Render deterministic alerts/evidence/age/assumptions/severity/lifecycle and ack separately; highlight attachments later FE-05 share same incident.
5. Loading/empty/error/degraded/unauthorized projections usable by keyboard; unresolved evidence cannot synthesize missing source event.

## 6. Output yang harus diserahkan

Runway/map/source context components usable via fixture port, wired App and styles; data semantics ready for replay timeline.

## 7. Asumsi dan unknown

**ASSUMPTION:** Baseline small object count fits SVG; local axes not labeled WGS84.

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
