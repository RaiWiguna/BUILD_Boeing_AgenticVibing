# AI-05 — Evaluator-only options dan structured summary validation

**Owner-role:** AI Harness

**Packet induk:** [ai-harness.md](../../packages/ai-harness.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan notes/opsi hipotetis offline yang menunjuk evidence, rationale, preconditions dan unknowns, tanpa executable action.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Belum ada SummaryProvider/options generator. Current detector explanation deterministic; provider JSON validity belum menjadi bukti factual support.

**TARGET:** Stub/local summary adapter, structured options dan result validation/revision linkage. Tidak membuka database sesi, memanggil command/clearance, mengubah severity, atau memakai audio live.

## 3. Context dan ownership

- [backend/detection.py](../../../../backend/detection.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §10.4, §14.2 dan §19.6.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `backend/ai_harness/options.py`

**File usulan dari task lain yang diperluas, belum ada:** `backend/ai_harness/providers.py`

Read-only model context; no tools/DB/command transport. BE-06 final scope/schema validator; FE-05 evaluator display. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. providers.py sesudah AI-03; worker AI-02 calls pipeline via configured provider port, not import BE service.

## 4. Kontrak dan dependency

**Contract:** SC-05 dan C-05/C-07/C-08. Fixed analysis/source/input/transcript revisions+public evidence→typed notes/options/result or safe error; no future/private truth context.

**Implementation dependency:** [AI-01](../ai-harness/AI-01-assist-dto-provider-ports.md), [AI-04](../ai-harness/AI-04-deterministic-evidence-reconciliation.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** StubSummary valid/invalid JSON/refs/actions, prompt-like transcript data; local provider optional through supplied config.

**Integration dependency:** AI-02 worker, BE-06 validator/storage, BE-07 review/FE-05.

## 5. Pendekatan implementasi

1. Build bounded public evidence context dengan IDs/time/versions and analysis window; no raw report truth/future scenario instructions.
2. Implement local SummaryProvider via supplied Ollama endpoint/model config or stub; explicit unavailable if local provider missing. JSON schema-constrained response then Pydantic validation.
3. Options mempunyai option_statement/rationale/typed supporting_evidence_ids/preconditions/unknowns/version/review status; every factual item references supporting evidence.
4. Reject extra command/clearance/control_action fields, hallucinated or foreign IDs; process transcript as data and give model no execution tools.
5. Partial/unsupported assumptions menjadi uncertainty/unresolved atau empty output dengan safe reason; candidate review status tidak auto-confirm; corrected input creates new analysis version.

## 6. Output yang harus diserahkan

Option/summary pipeline dengan traceable input/output versions dan failure states untuk offline evaluator review.

## 7. Asumsi dan unknown

**ASSUMPTION:** Local schema validation dan referential integrity mekanis; semantic relevance tetap evaluation task.

**UNKNOWN:** Model availability/factual support/advisory quality thresholds/domain relevance. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 owns generator/schema-negative tests; QA-03 full result sink. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Unit | Valid fixture rationale+evidence refs | `python -m pytest tests/unit/test_ai_05.py` | Option tetap unresolved/candidate, supporting refs/preconditions/unknowns tersedia. |
| Negative | Fabricated IDs, action field, prompt-like audio text | Command sama | Invalid result tidak masuk accepted output; tidak ada tool/command/source effect. |
| Degraded | Timeout/unavailable/insufficient evidence | Command sama | Safe failure/unknown/empty reason; no precision/authority claim buatan. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Option non-execution | BE-06/07+FE-05 evaluator and training seats | `python -m pytest tests/browser/test_options_boundary.py` | Option hanya di replay evaluator, review append-only, tidak dapat masuk command path. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
