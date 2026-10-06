# QA-05 — Native browser replay/review flows

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status QA-05 (6 Oktober 2026):** Suite browser diperbarui pada worktree `codex/qa04-mock-stack-launcher`, berbasis `1d4e3d044e9cf512f0b2bdeeae6692833cc448be`. Full `tests/browser` run saat ini: **2 passed, 21 skipped, 0 failed**. Dua pass adalah checks Playwright terhadap current API; browser UI, QA-04 launcher flow, dan stream reconnect checks diskip karena Vite lokal tidak tersedia. Ini bukan hasil historis 16 passed/1 xfailed.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memverifikasi UI mock dan real-API workflows melalui native Python Playwright, termasuk time/evidence/scope/outage/non-execution behavior.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (6 Oktober 2026):** FE-01–05 source, suite `tests/browser/`, QA-01 public synthetic fixtures, dan launcher QA-04 tersedia di checkout. Backend source mempunyai replay import/frame/evidence, transcript/highlight/option, assist stream, review, dan debrief routes. Chromium/Playwright tersedia, tetapi `frontend/node_modules` dan Vite lokal tidak ada; UI build/render serta UI/API browser flow tidak dijalankan. Keberadaan `frontend/dist` bukan bukti runtime.

**TARGET:** Producer FE browser modules, adapter parity, reconnect, map/timeline/audio/assist/correction/debrief/roles and visual usability checks. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [frontend/src/main.tsx](../../../../frontend/src/main.tsx)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [frontend/src/api.ts](../../../../frontend/src/api.ts)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §12, §16.3, §16.5.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** QA-05 suite browser sudah ada dari run terdahulu. Task ini memperbarui current API assertions, menambah current imported replay/API checks, reconnect/outage checks dan browser flow terhadap launcher QA-04, serta membuat run manifest menghitung setup skips/errors.

**Deliverable QA-05:** `tests/browser/` berisi conftest/lifecycle, FE-01–05 fixture/training flows, option boundary, current API checks, QA-04 mock browser flow, dan assist/source stream reconnect tests. Hasil hanya dinyatakan sesuai test yang benar-benar berjalan.

Native Python Playwright sesuai stack; QA owns every browser test named producer §8. Screenshots verify UI only, not geometry/rule correctness. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01–07, termasuk historical cutoff/evidence, source-read/evaluator scope, review receipts dan no option execute path. Fixture/mock dan current API dilaporkan terpisah. Current API browser check memakai public F-REPLAY-01 yang diproyeksikan secara lokal ke normalized import DTO backend; ini bukan mapping canonical QA-01 dan tidak membaca private fixture atau `benchmark-manifest.json`.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-04](../integration-qa/QA-04-mock-stack-launcher.md). QA-04 launcher tersedia, tetapi browser child Vite mensyaratkan `frontend/node_modules/vite/bin/vite.js` yang tidak ada. FE-05 inline fixture tetap merupakan profile berbeda dari F-COMM-01/F-REPLAY-01.

**Mock/stub:** Fixture/API-mock profile first, stub audio/result if missing local model; badges distinguish no audio/AI unavailable.

**Integration dependency:** FE-01–05+BE-04–07/SD result for actual runtime; mock frontend testing independent.

## 5. Implementasi dan cakupan aktual

1. `conftest.py` memulai current FastAPI pada loopback dengan SQLite sementara dan operator key sekali pakai. QA-04 mock server/Vite hanya dimulai oleh fixture `qa04_mock_stack` bila dependency Vite tersedia.
2. `test_mock_stack.py` memeriksa health/data-label `fixture-mock`, FE UI tetap `FIXTURE MODE`, label synthetic, audio bytes unavailable, dan tidak ada request command. Run ini **skipped** karena Vite tidak tersedia.
3. `test_fe_01.py`–`test_fe_05.py` memuat evaluator/training fixture, seek/frame/event/evidence cutoff, alignment unknown, transcript conflict/reconcile, debrief, no audio/provider, role projection, keyboard/focus dan viewport. Semua UI tests **skipped** pada run ini karena Vite tidak tersedia; provider badge xfail lama bukan hasil run sekarang.
4. `test_options_boundary.py` mempertahankan coverage evaluator-only, receipt states, alert severity/lifecycle, dan tidak ada command request dari kandidat/review. **Skipped** pada run ini karena Vite tidak tersedia.
5. `test_api_capability.py` menjalankan current-source role checks dan imported replay/API flow melalui Chromium `APIRequestContext`: replay frame <= requested time, evidence sampai receive-time cutoff, source-read vs evaluator/participant scope, frozen review seek, imported source read-only, debrief, no exposed execute route, empty transcript list dan worker/local model unavailable. Dua test lulus; satu API UI flow diskip karena Vite tidak tersedia.
6. `test_api_reconnect.py` menguji duplicate/gap sequence, transport outage/reconnect, dan source last-frame/reconnect snapshot memakai QA-04 mock stream. Semua **skipped** karena fixture launcher tidak dapat memulai Vite.
7. Source inspection menemukan FE adapter default `replay_assist_profile=False` pada `frontend/src/adapters/apiReplayReview.ts` (constructor) dan `frontend/src/App.tsx` membuat adapter tanpa profile capability. Ada pula teks `App.tsx` yang menyebut current backend tidak memiliki scoped assist routes; route tersebut kini ada di source. Ini temuan owner FE dan tidak diubah di QA-05.
8. Source stream adapter mengabaikan snapshot sequence duplikat sebelum memulihkan status `connected`; test source reconnect ditambahkan agar dapat menguji perilaku itu saat Vite tersedia. Ini belum dijalankan dan dicatat sebagai temuan FE, bukan hasil runtime.

## 6. Output yang harus diserahkan

Browser workflow/assertion suite di `tests/browser/` dan run manifest aktual: [result-manifest.json](../../../../tests/browser/artifacts/run-20261006T144251039122+0700/result-manifest.json). Manifest memiliki **tanpa screenshot** karena seluruh UI tests diskip. Tidak ada screenshot lama yang ditimpa/dihapus. Screenshot, jika kelak dihasilkan, memverifikasi rendering saja, bukan geometri, aturan domain, atau validitas operasional.

## 7. Asumsi dan unknown

**ASSUMPTION:** Browser contexts satu host menguji role/UI; tidak membuktikan human factors site atau real LAN.

**Belum diverifikasi:** QA-04 mock browser/stream flow, UI API mode, sequence-gap/duplicate behavior in browser, outage/reconnect runtime, dan current UI review/debrief belum berjalan karena Vite tidak tersedia. Direct API checks memakai Uvicorn current source dan temporary SQLite, bukan FE adapter integration. QA-01 F-REPLAY-01 manifest/events tidak langsung diterima strict backend import DTO; test menggunakan proyeksi lokal khusus test, sehingga canonical fixture-to-backend integration belum dibuktikan. Source-only debrief lulus; persisted transcript correction/highlight review tidak diuji karena import test tidak memiliki assist job/result. Tidak ada provider/ASR/audio bytes, domain review, codec/hardware assessment, partner data, LAN/human-factors review, fidelity mitra, QA-06 cold runtime, atau validasi operasional.

## 8. Test dan kriteria lulus

QA-05 owns browser runtime checks. Environment pada 6 Oktober 2026: Python 3.13.14, pytest 9.0.3, Playwright 1.60.0, Chromium binary tersedia dan berjalan untuk dua test API; Node 24.19.0 dan npm 11.17.0 tersedia, tetapi `frontend/node_modules`/Vite lokal tidak ada. Tidak ada dependency diunduh atau dipasang.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Fixture/evaluator & training UI | FE-05 authored inline fixture; test QA-04 menggunakan F-COMM-01 | `python -m pytest tests/browser/test_mock_stack.py` | **1 skipped**: `frontend/node_modules/vite/bin/vite.js` hilang. Tidak ada UI, screenshot, atau mock-stack browser runtime. |
| Compile test harness | File QA-05 `conftest.py`, `test_api_capability.py`, `test_api_reconnect.py`, `test_mock_stack.py` | `python -m py_compile tests/browser/conftest.py tests/browser/test_api_capability.py tests/browser/test_api_reconnect.py tests/browser/test_mock_stack.py` | Exit 0. Ini hanya pemeriksaan sintaks. |

Current API browser/API checks (current backend source, temporary SQLite, public synthetic replay only):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Role and imported replay API | Playwright Chromium/APIRequestContext + local FastAPI/Uvicorn + temp SQLite | `python -m pytest tests/browser/test_api_capability.py` | **2 passed, 1 skipped**. Role report/escalation denied; imported replay, cutoff/evidence, source-read scope, review seek, debrief pass. No UI flow or provider inference claimed. |
| Full current browser suite | Current API + UI/mocks | `python -m pytest tests/browser` | **2 passed, 21 skipped, 0 failed**. Skips all due missing local Vite. No screenshots were generated. This replaces neither the older 16 passed/1 xfailed result nor frontend build results; those are historical. |

Fixture/mock checks dan current API checks dilaporkan terpisah. Eksplorasi awal menemukan raw QA-01 fixture manifest/event payload ditolak backend import dengan 422 karena schema ketat/type-specific fields dan timebase berbeda; test memakai proyeksi lokal terbatas lalu final current API checks lulus. Ini bukan bukti canonical QA-01 ingestion. Expected failure provider badge historis tidak dieksekusi pada run sekarang. Screenshot tidak menjadi oracle domain; tidak menyatakan fidelity mitra, evaluasi trainer, atau validasi operasi.
