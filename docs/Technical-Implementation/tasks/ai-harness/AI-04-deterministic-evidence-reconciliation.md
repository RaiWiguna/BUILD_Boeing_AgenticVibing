# AI-04 — Deterministic evidence reconciliation

**Owner-role:** AI Harness

**Packet induk:** [ai-harness.md](../../packages/ai-harness.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghubungkan transcript/entity candidates dengan public event/alert evidence secara repeatable, dengan possible_link dan coverage uncertainty yang eksplisit.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Deterministic alerts current mempunyai evidence_event_ids; tidak ada transcript reconciliation; snapshot events hanya tail non-TRACK.

**TARGET:** Read-only reconciliation/highlight pipeline dan evidence resolution yang tidak menduplikasi hazard. Tidak membuka database sesi, memanggil command/clearance, mengubah severity, atau memakai audio live.

## 3. Context dan ownership

- [backend/detection.py](../../../../backend/detection.py)
- [backend/session.py](../../../../backend/session.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.2, §8.5, §10.4, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `backend/ai_harness/reconcile.py`

Public EvidenceReader saja; tidak memakai report truth/benchmark labels; detector severity immutable. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-02/05 dan C-02/C-03/C-05. Segments/entities/revision+public source events/alerts/window→AssistHighlight refs/uncertainty/link_status; consumer AI-05/BE-06/FE-05.

**Implementation dependency:** [AI-01](../ai-harness/AI-01-assist-dto-provider-ports.md), [AI-03](../ai-harness/AI-03-local-asr-transcript-entities.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** InMemoryEvidenceReader pada F-COMM-01, deliberately incomplete event/coverage data dan shared IDs versus timestamp-only pairs.

**Integration dependency:** BE-02/06 reader dan SD-04/05 alert evidence.

## 5. Pendekatan implementasi

1. Resolve candidate refs ke existing typed public evidence dengan same-source relation; reject invalid/dangling version relation.
2. Bandingkan recorded clearance/request/readback dan observed movement pada available receive time; temporal fixture C-03 mencegah before-receipt threat inference.
3. Shared entity/event identity yang relevan menghasilkan linked evidence; timestamp proximity saja possible_link tanpa auto-merge.
4. Missing counterpart dalam incomplete coverage atau alignment unknown menghasilkan review candidate/unknown, bukan absence fact.
5. Attach linked_alert_id untuk existing deterministic incident dan preserve review_priority terpisah severity; no new hazard duplicate or command.

## 6. Output yang harus diserahkan

Deterministic highlights/link evidence untuk BE commit/FE alert evidence panel dan read-only option generator.

## 7. Asumsi dan unknown

**ASSUMPTION:** Rule/config reconciliation version pinned di analysis; no operational phraseology claim.

**UNKNOWN:** Validity association/phraseology mitra membutuhkan domain evidence kelak. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki reconciliation unit tests. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Unit | SYN-COMM-01 event/segment IDs dan fixed versions | `python -m pytest tests/unit/test_ai_04.py` | Same inputs same highlights; link refs valid, detector incident tetap satu. |
| Negative | Missing clearance log coverage, unknown alignment, foreign ref | Command sama | Unknown/possible_link explicit; tidak menyatakan clearance tidak pernah diberikan. |
| Boundary | Changed private labels, unchanged public evidence | Command sama | Result tetap sama; no truth reads/severity changes/source mutation. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Evidence panel | BE-06 reader+SD alert+FE-05 | `python -m pytest tests/browser/test_evidence_links.py` | Highlight membuka source evidence valid pada incident existing; unresolved tidak dibuatkan event palsu. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
