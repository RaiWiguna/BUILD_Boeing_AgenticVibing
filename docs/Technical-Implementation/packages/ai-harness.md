# AI — Offline AI harness

**Owner-role:** AI Harness. **Status:** `TARGET/PROPOSED_CONTRACT`; tidak ditemukan implementasi AI current pada inspeksi 3 Oktober 2026. [Master](../README.md) · [Shared contracts](../shared-contracts.md).

## Objective dan output

Mengolah audio replay offline dan public evidence menjadi transcript hypothesis, candidate entities, deterministic reconciliation findings, serta opsi hipotetis evaluator yang mempunyai evidence/uncertainty. Jalur ini tidak mengubah source replay, severity detector, instruction/clearance, atau simulator state.

Deliverables implementasi: typed assist/worker DTOs, `ASRProvider` dan `SummaryProvider`, deterministic provider stubs, process-isolated worker, entity extraction/reconciliation, option-output validation dan failure states. BE menerima validated typed results untuk persistence/transport; FE menerima raw/corrected transcript serta evidence-linked candidates melalui BE; QA menerima provider-independent inputs/expected outputs untuk tests.

## CURRENT/TARGET dan scope

| Label | Kondisi |
|---|---|
| CURRENT_SOURCE | Backend mempunyai synthetic communications sebagai event/duration, detector evidence dan replay archive; bukan audio waveform/ASR |
| CURRENT_SOURCE | Tidak ditemukan audio asset store, ASR worker, transcript/option schema atau AI client pada files backend/frontend yang diperiksa |
| TARGET | Offline paired audio/event analysis; raw ASR, corrected revisions, hypothesis entities, reconciliation, evaluator-only options, outage isolation |
| UNKNOWN | Corpus berlabel mitra, ASR quality/critical-slot thresholds, diarization fidelity, hardware/model version/provisioning, aturan transfer data mitra |

Included: synthetic/permitted offline audio, timestamps/channel metadata, ASR confidence/alternatives bila provider tersedia, slot extraction, read-only reconciliation, notes/highlights/options, provider timeout/cancel/validation. Excluded: live microphone/VHF, production feed, cloud default, official transcript, automatic clearance, alert severity verdict LLM, safety/accuracy claim tanpa evaluation. Pilihan baseline `faster-whisper`/Ollama dalam addendum adalah rekomendasi target, bukan dependency yang sudah dipasang/dibuktikan.

## Context packet

| Sumber | Bagian relevan |
|---|---|
| [AI Assist Buddy](../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md) | §1.1–1.3, §3.1–3.5, §5 fixture/evaluation minimum |
| [Rencana Teknis MVP](../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md) | §6.2 truth isolation, §7.1/time, §10.4 evidence, §14.2 re-analysis |
| [Operational Reality Research](../../Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md) | §6 data access/quality dan §12.C AI assumptions; pertahankan certainty labels |
| [models.py](../../../backend/models.py), [session.py](../../../backend/session.py), [detection.py](../../../backend/detection.py) | Baca Track/Clearance/source event dan evidence output yang diterima; tidak mengedit |
| [review.py](../../../backend/review.py), [app.py](../../../backend/app.py) | Source versus review IDs, existing token scope/role; transport tetap owner BE |

Test AI existing tidak ditemukan. Ground-truth evaluator/private truth bukan context untuk provider/model yang dinilai.

## Modul/file ownership

AI memiliki file usulan `backend/assist_contracts.py` dan `backend/ai_harness/`: `providers.py`, `worker.py`, `entities.py`, `reconcile.py`, `options.py`. Semua belum ada. Domain contracts bebas dari imports Archive/Session/services; internal worker queue mengikuti SC-04 yang BE inject di composition root.

BE memiliki asset/job metadata, private paths, dispatch state/attempt IDs, authorization, durable result/revisions dan HTTP/WS (`assist_service.py`, `assist_storage.py`). AI tidak mengedit app/storage/session/models, tidak membuka SQLite, dan tidak membuat second writer. FE tidak menerima provider-specific payload; QA memiliki canonical fixture/tests. Dependency package Python tetap BE; AI menyampaikan kebutuhan provider yang benar-benar dipilih kelak.

## Inputs, outputs, kontrak dan consumer

| Interface / stage | Input | Output / consumer |
|---|---|---|
| SC-04 WorkerRequest | Validated asset reference/hash/mapping, job/attempt/model config | Progress dan WorkerResult ke BE |
| `ASRProvider.transcribe` | Audio chunks offline + channel/language hints | SC-05 TranscriptSegment hypotheses dengan audio-relative times |
| Candidate extraction | Raw atau explicit corrected transcript revision | CandidateEntity dengan raw/normalized value, alternatives, uncertainty |
| Reconciliation | Candidate entities + read-only public event/alert slice dari SC-02/05 | AssistHighlight dengan valid refs dan link/possible_link |
| `SummaryProvider`/option stage | Fixed replay_analysis_id, public evidence slice, schema constraint | AdvisoryOptionCandidate/notes untuk evaluator; tidak executable |
| Result validator | Output structured, source/model/input versions | Accepted result atau safe validation failure; BE tetap final commit validator |

Provider ports menggunakan model/config/version explicit. Stub output menyatakan `stub-1`, bukan fabricated ASR confidence/model measurement. Null confidence/unknown speaker/channel hanya ditampilkan unknown. Speaker metadata simulator lebih kuat dari diarization hypothesis; callsign tidak dianggap identitas orang.

SC-05 adalah satu shape untuk entities/highlights/options/annotations. ASR entity `instruction` tidak dikonversi menjadi model Clearance. `supporting_evidence_ids` typed refs tidak boleh berisi ID di source/session lain. Evidence inputs hanya authorized observations/events; transcript/rationale tidak diberikan tool command.

## Mock/stub/fixture mandiri

1. `StubASRProvider`: input synthetic asset/hash/chunk → fixed segments; variants clipped negation, wrong runway/callsign, null confidence, unknown speaker, mixed Indonesia/English, empty/no-speech, timeout/cancel. Label transcript authored/stub; tidak disebut ASR runtime.
2. `StubSummaryProvider`: evidence fixtures → option object SC-05; variants malformed JSON, fabricated event ID, cross-source refs, unsupported factual statement, action field, timeout. Model schema success terpisah dari factual support.
3. `InMemoryEvidenceReader`: hanya public events/alerts/segments/versions yang ditentukan fixture; deliberately incomplete coverage dan source alignment unknown. Tidak menyediakan ground truth untuk reconcile/model.
4. SYN-COMM-01 dari addendum: SEG-TWR-006, EVT-CLR-021, EVT-TRK-088, ALRT-009. Paired metadata memisahkan audio time/observed/received/session offset. QA memegang expected slot/evidence/links independent.
5. Dummy typed result sink tanpa Archive/HTTP; failure/duplicate attempts divalidasi bersama BE ketika runtime tersedia. Pipeline AI dapat selesai diuji mandiri menggunakan local stubs.

## Alur utama

1. Worker menerima validated immutable audio local reference dan fixed attempt/input/config versions. Baca file read-only; chunk timestamps mengacu asset timeline. Inferensi bukan dalam event loop/clock lock server.
2. ASR mengeluarkan hypotheses with start/end/channel/source/confidence/model version. Kata/slot tidak pasti tetap alternatives/unknown; metadata speaker tidak diisi dari tebakan callsign.
3. Normalize critical slots sambil mempertahankan raw text/value, negation dan correction revision basis. Bila mapping audio/session unknown, hasil transcript boleh ada sebagai unaligned review evidence tetapi tidak mengklaim urutan event.
4. Reconcile deterministic menghubungkan shared entity/event IDs dan time window yang diizinkan. Missing counterpart pada incomplete log → candidate dengan coverage/alignment uncertainty, bukan absence fact. Timestamp proximity saja → possible_link.
5. Kalau hazard sudah mempunyai detector alert, tambahkan highlight/evidence pada alert tersebut, jangan membuat duplicate alert. LLM tidak mengubah severity atau resolve alert.
6. Option provider memakai read-only replay slice dan schema untuk rationale/preconditions/unknowns/evidence. Output tidak mempunyai command/clearance action fields. Jika evidence cukup tidak tersedia, hasil unknown/unresolved atau kosong dengan alasan, bukan opsi presisi buatan.
7. Worker mengembalikan typed result; BE memverifikasi source/attempt/hash/version/evidence dan commit. Reviewer koreksi/confirm/dismiss/unresolved menjadi annotation baru server; rerun analysis menunjuk revisions baru dan tidak overwrite hasil asal.

## Failure/degraded cases

| Keadaan | Output/perilaku |
|---|---|
| Model/audio unavailable, asset invalid | Failed/unavailable job dengan safe error; source replay tetap berjalan |
| No speech atau chunk kosong | Empty successful transcript bila benar no-speech; dibedakan dari failed ASR |
| Low confidence/callsign/runway/negation ambiguity | Review-needed/alternatives; confidence tidak menjadi safety label |
| Speaker overlap/clip/unknown | Attribution unknown/candidate; jangan memalsukan source channel/person |
| Alignment/coverage/clearance counterpart unknown | Highlight berisi unknown/possible_link; tidak merge atau menerbitkan clearance |
| Hallucinated ID/action field/invalid type | Reject result atau candidate invalid dengan diagnostic aman; raw provider output tidak disiarkan sebagai valid |
| Timeout/cancel/retry/late result | Attempt cancellation/failed signal; BE menolak late/duplicate commit; worker tidak menggandakan effect |
| Prompt-like instructions dalam transcript/event text | Perlakukan data; no tool execution/source mutation; model tidak diberi tool clearance/storage |
| Provider changed/offline model missing | Explicit unavailable/config mismatch; tidak download atau cloud fallback diam-diam saat demo |

## Verification teknis / readiness-to-integrate

- Schema validation dan referential integrity atas fixture valid/invalid, typed evidence refs, same-source versions, nonempty rationale/unknowns dan no-action extra fields.
- Reconciliation repeatable dari fixture yang sama; timestamp alignment/uncertainty, raw entity alternatives dan possible_link tetap utuh; deterministic alerts tidak dimutasi/diduplikasi.
- Worker port dapat diuji tanpa FastAPI/SQLite; server clocks/replay tidak bergantung inference duration. Timeout/cancel/duplicate/late results diuji pada port, lalu integrated BE commit.
- Koreksi/review tidak overwrite raw ASR atau source structured event. Rerun dengan transcript revision berbeda menghasilkan analysis version terpisah.
- Opsi tidak dapat direpresentasikan sebagai Command atau dikirim ke command transport; negative action fields/extra instruction payload ditolak pada model/provider/server boundary.
- Jika provider riil dipasang kelak, ukur WER/CER, callsign/runway/instruction/number/negation errors, attribution/alignment error, per-session candidate FP/FN, latency chunk→display, evidence integrity dan correction count sesuai addendum §5. Pisahkan bahasa/noise/hardware/model/scenario/source; tidak buat angka target kualitas baru.
- Stub contract tests bukan pengujian ASR riil; synthetic corpus bukan fidelity operations. Relevance/unsupported assumptions options memerlukan reviewer ATCO yang belum tersedia; jangan auto-confirm candidate dari test lulus.

Readiness-to-integrate berarti typed result/stub tests sesuai kontrak, failure isolation dan provenance dapat diperiksa, lalu BE/FE integration checks dilakukan. Bukan approval/sign-off atau validasi domain.

## Asumsi dan unknown

**ASSUMPTION:** same-host worker process dan sederhana local queue cukup untuk baseline; local CPU model path dapat disediakan sebelum demo. Provider recommendation addendum tidak mengunci model patch/hardware karena belum dibuktikan.

**UNKNOWN:** actual offline model assets/hash/licenses, CPU/GPU/RAM, consent/corpus/ground truth mitra, language/accent performance, calibrated confidence, alignment drift, numeric ASR/advisory quality thresholds. Ketidaktersediaan ini tidak menahan pembangunan typed stub harness.
