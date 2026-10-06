# QA-04 — Mock stack launcher

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status QA-04 (6 Oktober 2026):** Source launcher dan contract tests tersedia di worktree `codex/qa04-mock-stack-launcher`. Mock HTTP/WS berhasil dimulai dan diprobe; full CLI berhenti sebelum Vite karena dependency frontend tidak terpasang (`frontend/node_modules` tidak ada). Ini bukan bukti UI runtime/build.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan satu launcher yang menjalankan replay/assist mock transport dan frontend explicit mode dengan cleanup serta private fixture isolation.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE baseline `origin/dev` (`1d4e3d0`):** FE React/Vite App dan fixture/API adapter tersedia; fixture publik `F-COMM-01`/`F-REPLAY-01` tersedia; backend replay/assist routes ada di source. `frontend/node_modules` tidak tersedia di checkout QA-04 dan `tests/browser/test_mock_stack.py` belum ada.

**TARGET:** Local mock HTTP/WS composition/launcher, fixture selection, isolated storage/credentials and process teardown. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [frontend/vite.config.ts](../../../../frontend/vite.config.ts)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.3–6.4, §12.4, §13.6–13.7.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru QA-04:** `scripts/run_mock_stack.py`, `tests/contracts/test_mock_stack.py`.

QA launcher/test files saja; FE owns UI mode/config, BE owns create_app injection and actual service. No permanent background service/network operations. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. CLI C-06 mock fixture→same SC-06 HTTP/WS and FE typed projection; consumer all UI/integration engineers.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-02](../integration-qa/QA-02-contract-unit-test-suites.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Pure fixture HTTP/WS handlers when BE addon routes absent, immutable memory archive/stub jobs; fixture-only UI can run separately.

**Integration dependency:** FE-01/02+BE composition seam, QA-05 browser sessions.

## 5. Pendekatan implementasi

1. Implementasikan CLI --fixture F-COMM-01 untuk memilih bundle F-*; validasi hash/profile dan jangan mengekspor private fixture.
2. Sajikan mock API localhost:8000 sesuai C-02/04/07, termasuk scoped identities/failed jobs/same-time events/reconnect injection; endpoint mock selalu berlabel.
3. Jalankan frontend dengan mode C-07 dan Vite localhost; badge fixture/API-mock terlihat pada UI.
4. Gunakan direktori temp dan test credential yang dibuat per run; jangan membaca runtime/operator-key riil; reset state fixture secara deterministic.
5. Tangani port terpakai, launch failure dan Ctrl+C dengan cleanup child processes/temp references; stdout menunjukkan mock URLs/profile/availability tanpa secrets.

**Implementasi QA-04:** Launcher memakai FastAPI/Uvicorn mock dalam proses, loopback `127.0.0.1` saja, fixture allowlist publik, temp storage dan kredensial random per run. Vite dijalankan sebagai child process langsung dengan env allowlist, `VITE_FLOWLENS_MODE=fixture`, evaluator view, temp `envDir`, loopback proxy, dan strict port. Mock melayani source frame/event/evidence dan assist projection/stream `assist-1`; additive replay-frame state menyatakan predictions/alerts `null` bila analysis unavailable, sementara current FE snapshot wire mempertahankan arrays dengan runway `UNKNOWN`/quality `unknown` dan label analysis unavailable. Transcript tetap stub, audio content unavailable, dan tidak ada command/option execution path. Response memberi mode/data-label headers. QA-only variants memakai public stub untuk failed job, event same-time ordering, duplicate/gap reconnect dan expired stream auth; variants tidak mengubah source fixture events. Shutdown mengakhiri Vite tree, thread server, config sementara, kredensial dan temp directory.

## 6. Output yang harus diserahkan

Launcher mock stack untuk frontend scaffold, tanpa dependency pada provider inference atau backend feature riil.

## 7. Asumsi dan unknown

**ASSUMPTION:** Port mock 8000 mengikuti Vite proxy; bind loopback, dengan port development frontend yang tercatat.

**Batas verifikasi:** Mock HTTP/WS berjalan pada loopback saat command QA-04 dijalankan. UI belum berjalan karena Vite dependency tidak tersedia; launcher tidak mengunduh dependency. Fixture tetap authored synthetic, transcript stub, tanpa audio bytes/provider, domain review, atau validasi operasional.

## 8. Test dan kriteria lulus

QA-04 owns `test_mock_stack.py`; producer mock behavior assertions tetap shared dengan QA-02. Hasil aktual pada Windows 11/Python 3.13.14 dicatat terpisah dari hasil QA-05/browser dan QA-06/package.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Launcher contract | F-COMM-01 and loopback temp server | `python -m pytest tests/contracts/test_mock_stack.py` | Routes/frames/evidence/job/candidate payloads follow proposed profile; private fixture unreadable. |
| Negative | Unknown fixture/schema, occupied port, interrupted launch | Command sama | Explicit error/no secret logging; child processes/temporary assets cleaned. |
| CLI | Selected fixture | `python scripts/run_mock_stack.py --fixture F-COMM-01` | Printed mock URLs/labels and actual transport availability; no downloads/live connections. |

### Hasil aktual QA-04

- `python -m py_compile scripts/run_mock_stack.py tests/contracts/test_mock_stack.py` — exit 0.
- `python -m pytest tests/contracts/test_mock_stack.py` — **12 passed, 6 dependency deprecation warnings** (Uvicorn/WebSockets). Run awal sebelum koreksi loader menghasilkan 3 passed/7 setup errors karena mengasumsikan `source_session_id` ada di replay manifest; validasi diperbaiki agar memakai public frame manifest dan suite diulang.
- `python scripts/run_mock_stack.py --fixture F-COMM-01` — mock HTTP health dan source/assist WS probes berhasil pada loopback; command exit 1 sebelum Vite start karena `frontend/node_modules/vite/bin/vite.js` tidak tersedia. Tidak ada dependency diunduh. URL, fixture/profile, label, dan status transport dicetak tanpa credential.
- Cleanup setelah command: port `127.0.0.1:8000` dan `:5173` dapat di-bind kembali; tidak ada direktori `atc-flowlens-qa04-*` atau config sementara `.qa04-vite-*.mjs` tersisa.
- Hash note: 15 public JSON/JSONL files berbeda pada exact-byte SHA-256 di checkout CRLF; seluruhnya cocok setelah CRLF→LF normalization. Perbedaan exact-byte QA-02 (9 passed, 1 failed) tidak diubah atau disembunyikan.
- `python -m pytest tests/browser/test_mock_stack.py` — **not run**: file QA-05 tersebut tidak tersedia di baseline `origin/dev`. FE build/UI runtime juga **not run** karena `frontend/node_modules` tidak tersedia.

Hasil ini membuktikan test contract dan mock transport runtime dalam harness/local process. Ini tidak membuktikan frontend build/render/browser integration, QA-05/API integration, QA-06 package/cold runtime, ASR/provider, domain review, atau validasi operasional.

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Mock browser | FE adapter/views against mock server | `python -m pytest tests/browser/test_mock_stack.py` | Setup/seek/evidence/correction run with fixture state; no calls to real provider/feed. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
