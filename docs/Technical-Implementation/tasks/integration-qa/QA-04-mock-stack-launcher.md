# QA-04 — Mock stack launcher

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan satu launcher yang menjalankan replay/assist mock transport dan frontend explicit mode dengan cleanup serta private fixture isolation.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** scripts existing berisi presentation tools; run_mock_stack.py belum tersedia; FE tooling/App incomplete.

**TARGET:** Local mock HTTP/WS composition/launcher, fixture selection, isolated storage/credentials and process teardown. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [frontend/vite.config.ts](../../../../frontend/vite.config.ts)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.3–6.4, §12.4, §13.6–13.7.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `scripts/run_mock_stack.py`, `tests/contracts/test_mock_stack.py`

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

## 6. Output yang harus diserahkan

Launcher mock stack untuk frontend scaffold, tanpa dependency pada provider inference atau backend feature riil.

## 7. Asumsi dan unknown

**ASSUMPTION:** Port mock 8000 mengikuti Vite proxy; bind loopback, dengan port development frontend yang tercatat.

**UNKNOWN:** Ketersediaan port/runtime baru dibuktikan saat launcher dijalankan. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-04 owns test_mock_stack.py; producer mock behavior assertions shared QA-02. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Launcher contract | F-COMM-01 and loopback temp server | `python -m pytest tests/contracts/test_mock_stack.py` | Routes/frames/evidence/job/candidate payloads follow proposed profile; private fixture unreadable. |
| Negative | Unknown fixture/schema, occupied port, interrupted launch | Command sama | Explicit error/no secret logging; child processes/temporary assets cleaned. |
| CLI | Selected fixture | `python scripts/run_mock_stack.py --fixture F-COMM-01` | Printed mock URLs/labels and actual transport availability; no downloads/live connections. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Mock browser | FE adapter/views against mock server | `python -m pytest tests/browser/test_mock_stack.py` | Setup/seek/evidence/correction run with fixture state; no calls to real provider/feed. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
