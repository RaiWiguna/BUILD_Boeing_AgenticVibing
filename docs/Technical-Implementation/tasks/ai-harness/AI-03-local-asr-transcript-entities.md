# AI-03 — Local ASR adapter, transcript, dan candidate entities

**Owner-role:** AI Harness

**Packet induk:** [ai-harness.md](../../packages/ai-harness.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menghasilkan transcript hypothesis bertimestamp serta critical-slot candidates dari audio offline, dengan provenance/alternatives dan explicit model availability.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Komunikasi current hanya text event/duration; tidak ditemukan ASR client/audio waveform pipeline. Python dependencies belum menyebut faster-whisper.

**TARGET:** Optional local ASR provider dan deterministic entity extraction untuk raw/corrected transcript revisions. Tidak membuka database sesi, memanggil command/clearance, mengubah severity, atau memakai audio live.

## 3. Context dan ownership

- [backend/session.py](../../../../backend/session.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.1/time, §8.5, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `backend/ai_harness/entities.py`

**File usulan dari task lain yang diperluas, belum ada:** `backend/ai_harness/providers.py`

BE-08 owns optional dependency declaration/provision config; worker AI-02 owns process. Speaker metadata lebih kuat dari diarization hypothesis. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. providers.py sesudah AI-01 dan sebelum AI-05.

## 4. Kontrak dan dependency

**Contract:** SC-04/05. Audio chunks/channel/config→TranscriptSegment→CandidateEntity callsign/runway/instruction/number/negation/time/actor-channel; C-03 causal time dan C-05 revisions.

**Implementation dependency:** [AI-01](../ai-harness/AI-01-assist-dto-provider-ports.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** StubASR fixed segments mixed Indonesia/English/clip/noise, null confidence and unknown speaker; extraction bisa diuji tanpa real model.

**Integration dependency:** AI-02 worker, BE-05 asset mapping dan BE-06 stored segments.

## 5. Pendekatan implementasi

1. Implement faster-whisper local adapter lazy optional; config local model path/version/hash, CPU INT8 baseline; GPU option only if explicit provision. Missing model returns unavailable, no download fallback.
2. Convert chunk-relative timestamps ke audio-relative asset times once; preserve channel/language/model identity and nullable confidence/alternatives.
3. Use simulator channel/speaker metadata when available; ambiguous audio mixed source retains unknown/hypothesis attribution, not guessed person identity.
4. Extract/normalize candidate critical slots deterministically preserving raw candidate/value/negation and corrected revision basis.
5. Do not convert extracted instruction ke source Clearance. Empty/no-speech successful output dibedakan provider failure.

## 6. Output yang harus diserahkan

ASRProvider local adapter dan entity extractor yang menghasilkan SC-05 typed candidates untuk reconciliation/options; explicit stub vs real flags.

## 7. Asumsi dan unknown

**ASSUMPTION:** Local model assets dipilih dari provisioned manifest; ukuran/patch tidak ditebak dari dokumen.

**UNKNOWN:** ASR critical-slot accuracy, accents/noise corpus dan calibrated confidence. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki stub/entity tests; provider riil memakai corpus berlabel terpisah. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Unit | Clipped negation/callsign/runway/code-switch segments | `python -m pytest tests/unit/test_ai_03.py` | Alternatives/raw value/negation/revision preserved; no automatic Clearance creation. |
| Negative | Missing model, no speech, speaker unknown | Command sama | Unavailable berbeda dari empty success; confidence unknown tidak diganti nol. |
| Contract | Chunk times+offset metadata | Command sama | Audio-relative start/end correct; source/receive/session times tidak dicampur. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Provider nyata | Provisioned model+QA-01 labeled corpus | `python -m pytest tests/integration/test_asr_provider.py` | Report WER/CER/critical-slot/attribution/alignment per profile/version/hardware; missing assets dilaporkan unavailable, tanpa quality pass buatan. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
