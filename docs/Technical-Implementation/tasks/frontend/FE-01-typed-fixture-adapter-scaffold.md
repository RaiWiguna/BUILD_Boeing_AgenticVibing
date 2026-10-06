# FE-01 — Typed replay port, fixture adapter, dan frontend scaffold

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status:** Partial implementation in source on 5 October 2026; frontend typecheck/build pass, while runtime, adapter QA, domain review, and operational validation are unverified.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan frontend yang dapat dibuild dengan typed port dan fixture mode eksplisit, tanpa backend/model sebagai prasyarat UI.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (5 October 2026):** `main.tsx`, `App.tsx`, `styles.css`, typed frontend contracts, fixture replay adapter, and an API dashboard adapter exist. API dashboard requests the existing local `/health`, scenarios, sessions, snapshot, and events routes with runtime shape checks. Frontend typecheck and build passed; backend/runtime status has not been checked. Existing wire types now include layout, route, source, and receive-time fields.

**TARGET:** Buildable React/TS/Vite scaffold, read-model contracts, deterministic `FixtureReplayReviewAdapter`, explicit source-mode state, and direct API access through an adapter. Tidak mengimplementasikan detector/provider/database atau memberi opsi AI jalur command.

## 3. Context dan ownership

- [frontend/src/main.tsx](../../../../frontend/src/main.tsx)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [frontend/package.json](../../../../frontend/package.json)
- [frontend/tsconfig.json](../../../../frontend/tsconfig.json)
- [frontend/vite.config.ts](../../../../frontend/vite.config.ts)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.3, §12.1–12.4, §13.6.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `frontend/src/types.ts`, `frontend/src/main.tsx`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`

**File baru usulan, belum ada:** `frontend/src/App.tsx`, `frontend/src/styles.css`, `frontend/src/contracts/replayReview.ts`, `frontend/src/adapters/fixtureReplayReview.ts`

UI read-model FE adapts backend wire; private fixtures/DB tidak diimpor component. Context adapter disediakan App. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. App/styles initial FE-01 lalu FE-03→FE-04→FE-05; FE-02 bebas mengerjakan api adapter.

## 4. Kontrak dan dependency

**Contract:** SC-02/05/07 dan C-02/C-04/C-07. ReplayReviewAdapter methods/read-model states→mock public source/frame/events/transcript/candidates/evidence/review receipts; consumer FE-03–05/QA.

**Implementation dependency:** Tidak ada output implementasi task lain yang wajib tersedia. Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Auth/quality/stream/correction authored fixtures; fixture mode label visible. Inline fixture boleh sebelum canonical QA-01 files.

**Integration dependency:** FE-02 API adapter parity dan QA-04/05 browser harness.

## 5. Pendekatan implementasi

1. Lengkapi App/styles dan declare required Vite/plugin/TypeScript/types dev dependencies dari tooling yang benar-benar dipakai; resolve lock sesuai runtime terpasang kelak.
2. Definisikan typed UI ports/read model/discriminated states dan runtime decoder shape C-02/07; no provider-specific payload page.
3. Implementasikan fixture adapter for source frames/events/transcript/evidence/control/review with deterministic clock, scoped projections and revision conflicts.
4. Pilih mode melalui config frontend eksplisit `VITE_FLOWLENS_MODE=fixture|api`, default fixture baseline; mode tidak berubah saat network error.
5. Sediakan adapter melalui App context and source/role/connection synthetic labels; no capture/live-connect action, candidate controls no command callback.

## 6. Output yang harus diserahkan

Buildable frontend shell, typed port dan mock adapter untuk UI tasks/tests; fixture output selalu labeled.

## 7. Asumsi dan unknown

**ASSUMPTION:** SVG/React and same-origin API default; fixture mode safe baseline.

**UNKNOWN:** Installed npm/runtime compatibility dibuktikan saat FE implementasi, bukan dari scripts yang ada. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02/05 owns adapter behavior checks. Build/typecheck commands were run for this implementation and their results are recorded in §9; the browser/adapter test commands below remain target checks and were not run.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Build/type | Completed scaffold and runtime tool lock | Dari `frontend/`: `npm run typecheck` dan `npm run build` | No missing imports/type errors; dist bundle terbangun dari declared tooling. |
| Contract | Adapter valid/error/degraded states | `python -m pytest tests/browser/test_fe_01.py` | UI menggunakan typed projection; mock clock/version/revisions konsisten, no private payload. |
| Negative | Unauthorized source ID/unsupported shape | Command sama | Explicit unauthorized/error state; tidak memilih fixture source pertama secara diam-diam. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Adapter parity | Same canonical public fixtures via FE-02 API | `python -m pytest tests/browser/test_adapter_parity.py` | Fixture/API menghasilkan semantik read-model sama dengan mode label berbeda. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.

## 9. Progress aktual — 5 Oktober 2026

- **Source ada:** `App.tsx`/`styles.css`, typed contracts, deterministic fixture adapter, explicit `VITE_FLOWLENS_MODE`, and local API dashboard adapter are present. FE-02 adds replay API decoding/auth/reconnect; historical frame-at-time and assist route runtime support remain unavailable until the backend implements them.
- **Build/typecheck:** `npm run typecheck` passed; `npm run build` passed with Vite 8.3.2 and emitted `frontend/dist/`.
- **Runtime/API integration:** not run; backend process and API responses have not been observed.
- **Tests, domain review, operational validation:** not run / not established.
