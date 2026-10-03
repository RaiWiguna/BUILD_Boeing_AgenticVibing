# QA-02 — Contract dan independent unit test suites

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menguji seluruh ports/DTOs/pure behavior dengan canonical fixtures dan stubs sebelum full runtime digabung.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** pyproject declares pytest/httpx/Playwright optional dan testpaths tests; executable test suite belum ada.

**TARGET:** Fixture validation, producer contract/unit assertions BE/SD/AI, transport/read-model parity dan failure variants. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [pyproject.toml](../../../../pyproject.toml)
- [backend/models.py](../../../../backend/models.py)
- [backend/detection.py](../../../../backend/detection.py)
- [frontend/src/types.ts](../../../../frontend/src/types.ts)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §16.1–16.2, §16.4.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `tests/contracts/`, `tests/unit/`

QA owns semua contract/unit modules termasuk test_be_01/test_sd_*/test_ai_* yang disebut producer tasks; FE behavior browser modules milik QA-05. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. SC profile fixtures + implementation/stub callable ports→assertions independent and actual result diagnostics; consumer every producer.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** FakeSource/FakeDetector/FakeLifecycle/FakeWorker/MemoryReader typed fixtures; stub default no ASR assets required.

**Integration dependency:** Contract/runtime adapters semua paket; actual implementation assertions tidak ditandai pass hanya dari stub tests.

## 5. Pendekatan implementasi

1. Implement fixture validator dan module-level contract tests producer paths sesuai test registry indeks, no file-existence-only checks.
2. Parametrize valid/invalid units/source/time/scope/version/action fields; independent formula for ETA/geometry/complexity/ages.
3. Implement reducer, clock/delay/RNG restore, predictions/rules/lifecycle and reconciliation/generator/provider-stub tests from task §8 assertions.
4. Separate mock contract tests yang dapat jalan awal dari implementation tests requiring future modules; missing module pending/unavailable bukan passing implementation.
5. Require deterministic comparisons excluding generated UUID/audit wall times; collect actual fixture/schema/config versions in failure output.

## 6. Output yang harus diserahkan

Meaningful contract/unit suites dan fake ports for semua producer; unsupported/unknown conditions tested without dependency on real model.

## 7. Asumsi dan unknown

**ASSUMPTION:** pytest project stack; dependency/install config remains BE-08 ownership.

**UNKNOWN:** Actual pass/build/runtime evidence only after implementations/modules exist. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

Task ini membuat tests executable kelak; seluruh command tetap target saat dokumentasi disusun. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Contract | Canonical F-* valid/invalid bundles | `python -m pytest tests/contracts` | Expected accept/reject/ref isolation identical among producers/consumers. |
| Unit | Independent analytic/rule/time/reconcile fixtures | `python -m pytest tests/unit` | All task assertions implemented; failures show exact input/version, no copied implementation oracle. |
| Negative | Intentional wrong interval/ref/extra action in fixture | Command di atas | Tests fail on introduced violation; missing implementation not reported as pass. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Real ports | Replace mocks with BE/SD/AI/FE implementation | `python -m pytest tests/contracts tests/unit` | Implementation adapters pass same contract fixtures; stub pass separately labeled. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
