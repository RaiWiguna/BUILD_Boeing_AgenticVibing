# FE-02 — API adapter, scoped credentials, dan reconnect

**Owner-role:** Frontend

**Packet induk:** [frontend-replay-review.md](../../packages/frontend-replay-review.md)
**Status per 5 Oktober 2026:** implementasi adapter/decoder tersedia di source frontend; `npm run typecheck` dan `npm run build` berhasil. REST/WS runtime, QA tests, domain review, dan validasi operasional belum dijalankan.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghubungkan ReplayReviewAdapter ke existing/additive REST/WS tanpa page fetch, scope escalation atau silent fixture fallback.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE sebelum FE-02:** API helper belum melakukan validasi runtime atau menyediakan authenticated stream adapter. Vite proxy `/api` dan WebSocket ke `localhost:8000`.

**FE-02 source sekarang:** `ApiDashboardAdapter` memakai decoder snapshot/event yang memvalidasi payload; `ApiReplayReviewAdapter` memakai satu transport injectable untuk REST/WS, credential in-memory terpisah (`source_read`, `review_control`, `reviewer`), error/status bertipe, kontrol replay, pembatasan event sampai waktu replay, dan reconnect/resync berurutan. Komponen React tetap memakai adapter.

**Batas integrasi:** source backend saat ini belum menerbitkan source-read/reviewer credential terpisah. Endpoint history frame-at-time dan route replay/assist additive belum tersedia. Adapter menandai capability yang absen sebagai unavailable/unsupported; keberadaan decoder terhadap profil usulan bukan bukti route runtime.

## 3. Context dan ownership

- [frontend/src/api.ts](../../../../frontend/src/api.ts)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [frontend/vite.config.ts](../../../../frontend/vite.config.ts)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §13, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `frontend/src/api.ts`

**File baru usulan, belum ada:** `frontend/src/adapters/apiReplayReview.ts`

FE adapter owns fetch/headers/serialization/errors; pages hanya port. BE endpoint belum ada ditampilkan unavailable, bukan fabricated backend success. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-02/05/06/07 dan C-02/C-04/C-07/C-08. API current direct snapshots dan additive replay/assist reads→SC-07 projections; review controls convert UI ms to SEEK seconds; capability source-read terpisah.

**Implementation dependency:** [FE-01](../frontend/FE-01-typed-fixture-adapter-scaffold.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Mock HTTP/WS transport exact route fixtures dan errors, recorded main/assist snapshots dengan independent sequence.

**Integration dependency:** BE-04–07 routes, QA-03/04 mock server dan FE-03–05 views.

## 5. Pendekatan implementasi

1. Decode current snapshot including layout/route/source/receive fields; discriminate imported frame shape C-02, jangan mengarang scenario/seed metadata.
2. Use review-control token untuk review ID dan source-read token untuk immutable source endpoints; credentials in memory/headers, no URL/query/localStorage secrets.
3. Implement time/cursor/scope-aware frame/events/transcript/evidence/job/options methods and cancellation; typed failures detail current JSON string/list handled.
4. WS first message token; repeated sequence snapshots acceptable, old frames/gaps trigger scoped full resync, separate source/assist sequence; cleanup subscriptions on source switch/expiry.
5. Handle 401 clear restricted projection, 403 denied, 409 refresh/reconcile unsent change, unsupported version error. Audio load uses credentialed fetch and object URL, revoked after playback/source switch; never cloud/fixture failover.

## 6. Output dan cakupan source

API adapter, injectable mockable HTTP/WebSocket transport, decoder wire untuk snapshot/frame/events/transcript/evidence/job/options/review receipt/source dan assist WebSocket message, serta auth/time/error/reconnect behavior tersedia di source frontend. Tidak ada file executable QA test atau fixture di namespace `tests/` yang ditambahkan.

| Capability | Status route menurut `backend/app.py` pada branch ini |
|---|---|
| `/health`, `/api/v1/scenarios`, `/api/v1/sessions`, `/api/v1/sessions/{id}`, `/snapshot`, `/events`, `/commands`, `/stream`, `/reviews`, `/branches`, `/seats` | Ada di source backend; belum diverifikasi saat runtime. Adapter memakai route snapshot/events/commands/stream dan metadata yang sesuai. |
| Historical `loadFrame(at_ms)` | Tidak ada route frame-at-time. Adapter membaca snapshot existing hanya jika waktu snapshot cocok; selain itu melempar error bertipe `unsupported_profile`. |
| `/replay-source`, `/transcription-jobs`, `/transcripts`, `/highlights`, `/replay-analyses/{analysis_id}/options`, corrections, review candidate, `/assist-stream` | Diusulkan pada SC-06, tidak ditemukan di source backend branch ini. Read/write REST dapat diberi opt-in capability untuk mock/profil berikutnya; 404 route additive dipetakan ke `unavailable`. Assist WS tidak dibuka kecuali capability opt-in. |
| Evidence resolver | Tidak ada route resolver. Adapter dapat resolve `session_event` dari route events; refs transcript/alert dilaporkan `unavailable` sampai pembacaan sumber waktunya tersedia. |

Route `POST /api/v1/sessions/{id}/reviews` saat ini mengembalikan review token saja; token sumber-read dan reviewer terpisah belum diterbitkan backend. Adapter tidak menukar atau menaikkan scope token secara otomatis.

## 7. Asumsi dan unknown

**ASSUMPTION:** Same-origin release and localhost proxy development, no token in media URL.

**UNKNOWN:** API/WS belum dijalankan terhadap backend, server mock QA, atau simulator mitra. Dukungan route additive, issuer capability yang terpisah, perilaku audio browser, serta reconnect saat server nyata perlu diverifikasi pada integrasi berikutnya. Tidak ada klaim domain review atau validasi operasional.

## 8. Test dan kriteria lulus

QA-05 owns browser transport contract tests with mock server. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Contract | Current/target HTTP and WS wire fixtures | `python -m pytest tests/browser/test_fe_02.py` | Fields decoded, frame/analysis/source IDs correct, SEEK unit conversion once. |
| Negative | 401/403/409/422/unknown profile and cross-source token | Command sama | Correct typed state, no scope escalation or silent fixture replacement. |
| Reconnect | Repeated/outdated/gap snapshots and abort | Command sama | Latest authorized full snapshot resync; no duplicates/late state from switched source. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Real API | BE-04–07 scoped routes+audio | `python -m pytest tests/browser/test_api_reconnect.py` | Controls/reads use correct credential and time/window; disconnect source vs assist isolated. |

Typecheck/build frontend lulus pada 5 Oktober 2026. Assertion QA dan integrasi real API pada tabel di atas belum dijalankan; task belum dinyatakan lulus acceptance runtime. Source/build tidak membuktikan provider, domain review, fidelity mitra, atau validasi operasional.
