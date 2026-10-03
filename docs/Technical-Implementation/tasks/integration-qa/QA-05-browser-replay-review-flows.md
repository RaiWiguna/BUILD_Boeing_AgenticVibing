# QA-05 — Native browser replay/review flows

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memverifikasi UI mock dan real-API workflows melalui native Python Playwright, termasuk time/evidence/scope/outage/non-execution behavior.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Playwright optional dependency ada; browser tests/UI modules belum ada dan dist belum terbangun.

**TARGET:** Producer FE browser modules, adapter parity, reconnect, map/timeline/audio/assist/correction/debrief/roles and visual usability checks. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [frontend/src/main.tsx](../../../../frontend/src/main.tsx)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [frontend/src/api.ts](../../../../frontend/src/api.ts)
- [frontend/package.json](../../../../frontend/package.json)
- [backend/app.py](../../../../backend/app.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §12, §16.3, §16.5.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `tests/browser/`

Native Python Playwright sesuai stack; QA owns every browser test named producer §8. Screenshots verify UI only, not geometry/rule correctness. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. Mock/API endpoints+same F-* fixtures+four role contexts→browser results and screenshots actual; FE and BE consumers.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-04](../integration-qa/QA-04-mock-stack-launcher.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Fixture/API-mock profile first, stub audio/result if missing local model; badges distinguish no audio/AI unavailable.

**Integration dependency:** FE-01–05+BE-04–07/SD result for actual runtime; mock frontend testing independent.

## 5. Pendekatan implementasi

1. Buat harness browser fixture/API-mock dengan lifecycle server dan config eksplisit; implementasikan test_fe_01..05 dan seluruh shared browser case di registry.
2. Jalankan setup→map→seek→evidence→transcript correction/review→debrief/export; assert actual frame time dan tidak ada future event sebelum receipt.
3. Assert nol option→commands network request; training seat tidak mendapat opsi; dropdown role tidak memberi privilege; source-read credential sesuai scope.
4. Inject sequence gap/expired auth/409/stale data/AI timeout/unknown alignment dan periksa state terpisah serta source replay tetap usable.
5. Periksa keyboard/focus/viewport sempit/label/clipping serta console/network errors. Uji contexts instruktur dan peserta tower/ground/observer sesuai fitur; evaluator adalah capability instruktur, bukan role baru.

## 6. Output yang harus diserahkan

Browser workflow/assertion suites dan screenshots/result manifest dari pelaksanaan aktual setelah UI tersedia.

## 7. Asumsi dan unknown

**ASSUMPTION:** Browser contexts satu host menguji role/UI; tidak membuktikan human factors site atau real LAN.

**UNKNOWN:** Hasil browser/audio codec/hardware dan evaluasi domain belum tersedia. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-05 owns browser runtime checks; install/provision toolchain by BE/FE owner before executing. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Mock browser | QA-04 F-COMM-01 or FE fixture mode | `python -m pytest tests/browser -k 'fe_ or mock_stack or adapter_parity'` | User interactions update correct refs/revisions/frame times and mode/source labels. |
| Negative UI | Clipped/missing/unknown/unauthorized/conflict/outage fixtures | Command sama | No fabricated success/evidence/fresh clear; keyboard and error recovery usable. |
| Action boundary | Imperative option text and reviewer buttons | `python -m pytest tests/browser/test_options_boundary.py` | No commands request issued, deterministic alert stays unchanged. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Real API E2E | BE+SD+AI stub/worker+FE complete stack | `python -m pytest tests/browser` | Persisted raw/corrected source evidence matches refreshed UI; reconnect/outage/scope/audio checks pass with actual API. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
