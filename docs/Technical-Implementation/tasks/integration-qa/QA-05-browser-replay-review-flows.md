# QA-05 — Native browser replay/review flows

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** Harness QA-05 dan pemeriksaan source yang tersedia diimplementasikan serta dijalankan pada 6 Oktober 2026. Fixture/browser dan current-API checks lulus; satu expected failure merekam provider state FE yang tampil `Unknown`. Additive replay/assist API E2E, QA-01 bundle, dan QA-04 launcher belum tersedia.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memverifikasi UI mock dan real-API workflows melalui native Python Playwright, termasuk time/evidence/scope/outage/non-execution behavior.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE (6 Oktober 2026):** FE-01–05 UI source ada dan native Playwright/Chromium tersedia. `tests/browser/` kini berisi QA-05 harness. QA-01 canonical fixture bundle dan `scripts/run_mock_stack.py` milik QA-04 tidak ada. Vite UI dapat dijalankan; keberadaan `frontend/dist` tidak dipakai sebagai bukti runtime.

**TARGET:** Producer FE browser modules, adapter parity, reconnect, map/timeline/audio/assist/correction/debrief/roles and visual usability checks. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [frontend/src/main.tsx](../../../../frontend/src/main.tsx)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [frontend/src/api.ts](../../../../frontend/src/api.ts)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §12, §16.3, §16.5.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Sebelum pekerjaan ini tidak ada browser test QA-05.

**Deliverable QA-05:** `tests/browser/` berisi conftest/lifecycle, FE-01–05 flows, option boundary, current API scope checks, dan run artifacts.

Native Python Playwright sesuai stack; QA owns every browser test named producer §8. Screenshots verify UI only, not geometry/rule correctness. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. Mock/API endpoints+same F-* fixtures+four role contexts→browser results and screenshots actual; FE and BE consumers.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-04](../integration-qa/QA-04-mock-stack-launcher.md). Kedua packet belum memiliki executable output. QA-05 memakai FE-05 inline fixture berlabel authored synthetic dan stub milik QA-05; ini bukan F-COMM-01 QA-01 atau launcher QA-04.

**Mock/stub:** Fixture/API-mock profile first, stub audio/result if missing local model; badges distinguish no audio/AI unavailable.

**Integration dependency:** FE-01–05+BE-04–07/SD result for actual runtime; mock frontend testing independent.

## 5. Implementasi dan cakupan aktual

1. `conftest.py` menjalankan Vite terpisah untuk evaluator fixture, training fixture, dan API mode. Current API check memakai proses FastAPI dari source, temporary SQLite, serta throwaway operator key; proses dibersihkan saat suite berakhir.
2. `test_fe_01.py` memeriksa source/setup, map, seek, frame aktual dan event cutoff pada timeline. Session snapshot tail tetap tampil dalam panel terpisah dengan timestamp snapshot-nya.
3. `test_fe_02.py` memeriksa typed refs, link relationship, possible-link, unresolved cutoff, unknown alignment tanpa audio/replay sync, serta `unavailable` dari adapter tanpa source-read credential.
4. `test_fe_03.py` memeriksa raw/corrected text, provenance, confidence nullable, dan conflict yang mempertahankan draft sampai refresh/reconcile serta retry dengan request ID baru.
5. `test_fe_04.py` memeriksa debrief, no audio bytes, training projection tanpa options, dan tidak membaca report instructor. Provider-unavailable badge ditandai expected failure karena subscription projection mengganti status menjadi `Unknown`.
6. `test_options_boundary.py` memeriksa opsi evaluator-only, status pending/accepted/conflict/unauthorized/unavailable/error dengan delayed QA stub, serta tidak ada request command saat kandidat/review dipakai dan alert severity/lifecycle tetap.
7. Current API browser checks memastikan replay/assist tambahan tetap unavailable, route transcript aktual 404, tanpa fallback fixture; role `tower`, `ground`, dan `observer` tidak dapat membaca report instructor atau menerbitkan seat instructor.
8. `test_fe_05.py` memeriksa viewport sempit, keyboard/focus, clipping horizontal, console dan request failures.

## 6. Output yang harus diserahkan

Browser workflow/assertion suites di `tests/browser/` dan screenshot/result manifest dari pelaksanaan aktual. Manifest run penuh 6 Oktober: [result-manifest.json](../../../../tests/browser/artifacts/run-20261006T121244317654+0700/result-manifest.json). Screenshot memverifikasi tampilan UI saja, bukan geometri, kebenaran domain, atau validitas operasional.

## 7. Asumsi dan unknown

**ASSUMPTION:** Browser contexts satu host menguji role/UI; tidak membuktikan human factors site atau real LAN.

**Belum diverifikasi:** sequence-gap injection, token expiry aktual, reconnect/outage WebSocket, dan persistence correction/review server-side belum dapat dijalankan terhadap route source yang tersedia. API run hanya menguji API legacy yang nyata; tidak mengklaim additive assist/transcript/evidence/audio/options integration. Tidak ada review domain, codec/hardware assessment, partner data, atau validasi operasional. Fixture/stub bukan hasil ASR, provider, partner, atau server.

## 8. Test dan kriteria lulus

QA-05 owns browser runtime checks. Dependency runner tersedia dan command berikut benar-benar dijalankan pada 6 Oktober 2026 dari root repository:

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Fixture browser | FE-05 authored inline `fixture-1`; tidak memakai QA-01 bundle/QA-04 launcher | `python -m pytest tests/browser -k 'fe_ or mock_stack or adapter_parity'` | **8 passed, 1 xfailed, 8 deselected**. Setup/map/seek/cutoff/evidence/review/debrief/training/focus checks lulus; provider-unavailable badge adalah expected failure. |
| Action boundary + receipt states | FE-05 UI dan delayed QA-owned stub pada ReviewEditor | `python -m pytest tests/browser/test_options_boundary.py` | **6 passed**. Tidak ada command request dari opsi/review; deterministic alert tetap ACTIVE/DATA_DEGRADED; semua enam state receipt dibedakan termasuk pending. |

Current API browser checks (backend legacy dijalankan aktual; bukan additive replay/assist integration):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Existing API/runtime scope | Local FastAPI current source + temp SQLite, Vite API mode | `python -m pytest tests/browser` | **16 passed, 1 xfailed**. Login/create/end/open-review jalan; additive transcript route 404 dan assist/source-read/options tetap unavailable; participant roles ditolak dari report/role escalation. Bukan bukti persisted correction, audio, worker, atau full API E2E. |

Fixture/mock checks dan current API checks dilaporkan terpisah. Expected failure adalah temuan source FE, bukan pass untuk provider-unavailable badge. Screenshot tidak menjadi oracle domain; tidak menyatakan fidelity mitra, evaluasi trainer, atau validasi operasi.
