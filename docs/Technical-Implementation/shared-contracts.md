# Shared contracts — SC

**Status:** `CURRENT_SOURCE` dipisahkan dari `PROPOSED_CONTRACT`, 3 Oktober 2026. Dokumen ini menyatukan interface agar BE/SD/AI/FE/QA dapat bekerja memakai mocks. Tidak ada schema/API baru yang dibuat. Batas dan ownership ada di [master](README.md).

## SC-01 — Source replay, provenance, timebase, quality

Dasar: [plan §7](../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#7-data-waktu-geometri-dan-simulator), [addendum §3](../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md#3-rancangan-backend), source [Track](../../backend/models.py), [event](../../backend/session.py), [Simulator](../../backend/simulator.py).

### CURRENT_SOURCE

`Track` adalah Pydantic extra-forbid dengan `id`, `callsign`, `kind`, `x_m`, `y_m`, `speed_mps`, `heading_deg`, `phase`, `length_m`, `width_m`, `runway`, `route`, `owner`, `observed_ms`, `received_ms`, `source`, `event_id`. Runway direction terbatas `09|27`, owner `tower|ground`. Snapshot menambah `stale` tanpa menjadikannya field input `Track`.

Event current berupa dict, bukan union Pydantic: `id`, `ordinal`, `sim_ms`, `audit_utc`, `type`, `message`, serta fields menurut type. TRACK mempunyai `target`, `observed_ms`, `received_ms`, `track`; CLEARANCE mempunyai `target`, `issuer`, `channel`, `duration_ms`, `instruction`, `runway`, `received_ms`. `audit_utc` dan metadata `created_utc` adalah float epoch **detik**; `server_sent_utc_ms` adalah epoch **ms**. Jangan menyamakan satuannya.

### PROPOSED_CONTRACT: import profile `replay-1`

Gunakan sidecar manifest dan record wrapper; jangan menambahkan provenance bebas ke `Track` current yang extra-forbid. Ini normalized internal/import profile, bukan format vendor atau replacement stream lama.

| Tipe / owner | Field minimum dan semantik |
|---|---|
| `ReplaySourceManifest` / BE | `schema_version`, `source_id`, `source_kind` (`synthetic` atau `authorized_simulator_replay`), `source_ref`, `content_hash`, `provenance`, `permission_profile`, `retention_until`, `timebase`, `coverage`, `layout` |
| `provenance` | Owner sumber, versi/export reference dan derivasi yang diketahui; field vendor yang tidak tersedia ditandai unknown. Tidak menyatakan izin berdasarkan URL publik |
| `permission_profile` | Reference tujuan/izin penggunaan dan batas pemrosesan yang dicatat; synthetic memakai profile lokal synthetic. Mitra tanpa informasi penggunaan tidak diproses sebagai authorized |
| `retention_until` | Timestamp UTC atau null dengan alasan pada provenance; null bukan izin penyimpanan tanpa batas |
| `timebase` | Nama clock/unit sumber, `mapping_id`, offset/mapping ke session ms, uncertainty dan status alignment; mapping unsupported menjadi unknown |
| `coverage` | Object/source/channel IDs yang memang tercakup, interval coverage dan missing intervals; jangan mengambil roster dari private scenario schedule |
| `layout` | Public geometry versi yang diperlukan SD/FE; baseline mengikuti `LAYOUT`, import harus menyatakan local axes/unit/direction mapping |
| `ReplayEventRecord` / BE | `schema_version`, `source_id`, `source_event_id`, `source_time`, `event`, `quality` |
| `event` | Event source simulator dengan ID internal `event.id`, `ordinal`, `sim_ms` dan data type-specific. TRACK tetap memakai shape `Track` current; replay import mempertahankan source IDs di wrapper |
| `quality` | Status `nominal`, `missing`, `stale`, `invalid`, atau `alignment_unknown` dan reasons; freshness dihitung pada waktu replay, sedangkan quality sumber dipertahankan terpisah |

`source_time` menyimpan nilai/unit/clock asal, termasuk null jika tidak diberikan; `event.sim_ms` adalah waktu event tersedia bagi state (receive time pada replay). TRACK `observed_ms` adalah waktu sample yang dinormalisasi dan `received_ms` waktu penerimaan pada session clock. Jangan mengisi observed time dari receipt untuk menutupi missing source timestamp. Event tanpa waktu yang dapat dipetakan boleh disimpan sebagai unresolved import record, tetapi tidak dipakai untuk prediksi timestamped sampai alignment jelas.

Stable internal IDs ber-namespace source/session; identitas tetap ID, bukan callsign. ID sumber duplikat dan payload identik bersifat dedup; ID sama dengan payload berbeda adalah import conflict. Order state: normalized receive time, lalu ordinal untuk ties. Out-of-order sample disimpan di log, tetapi latest state per `(source_id, object_id)` tidak mundur. Source event auth tidak berarti clearance dunia nyata: otoritas di sini hanya structured event simulator yang menyediakan rekaman.

Posisi/route/layout meter LOCAL_METRES, speed m/s, heading terhadap +x counterclockwise. Imported coordinates harus dikonversi dengan transform eksplisit; tidak dianggap WGS84. `observed_ms`/`received_ms`/`sim_ms` nonnegative finite integers. Missing dimensions/route/time tidak diganti nol; unsupported input dicatat sebagai invalid/degraded.

**ASSUMPTION:** mock menggunakan offset konstan `session_ms = source_ms + offset_ms`; audio menggunakan `session_ms = audio_ms + audio_offset_ms`. Manifest harus mencatat uncertainty/mapping version. Drift riil/vendor nonlinear adalah `UNKNOWN`; adapter menolak mapping yang tidak didukung, bukan mengasumsikan offset konstan akurat untuk mitra.

## SC-02 — Session state, historical replay dan partitions

### CURRENT_SOURCE

`Session.snapshot()` mengeluarkan `session_id`, `kind: training`, `sequence`, `sim_ms`, `revision`, `status`, `speed`, `metadata`, `layout`, `tracks`, `clearances`, `requests`, `predictions`, `runway`, `alerts`, `events`, `acknowledgements`, `assessments`, `complexity`, `error`. Metadata memuat scenario, seed/config, `engine_version`, `config_version`, kind/parent dan created UTC. `Manager.snapshot()` menambah `seat` dan `server_sent_utc_ms`, serta role/condition redaction.

`Review.snapshot()` mengganti ID/kind/revision/sequence/status/speed dan menambah `source_session_id`, `review_end_ms`, `playback_ms`, `review_annotations`. `sim_ms` tetap waktu frame source; `metadata.id` tetap source ID. Kind wire lowercase `training|review`. Review control menggunakan `START`, bukan `PLAY`.

`Archive.frame(source_id, target_ms)` memilih frame terakhir `sim_ms <= target_ms`; public/private tuple tidak boleh diekspor seluruhnya. `Snapshot.events` hanya tail non-TRACK; history/evidence lengkap diambil dari event archive. `sequence` bukan event cursor; `revision` adalah control/command revision; repeated WS snapshot dapat mempunyai sequence sama.

### PROPOSED_CONTRACT: ports dan isolation

| Port / owner BE | Operasi minimum (notasi internal, bukan endpoint) | Mock |
|---|---|---|
| `ReplayEventSource` | `manifest()`, `read(after_ordinal, until_ms)` → ordered `ReplayEventRecord[]` | Fixture source deterministic tanpa database |
| `ReplayArchiveReader` | `metadata(source_session_id)`, `frame(source_session_id, at_ms)`, `events(source_session_id, after_ordinal, until_ms)` | Public frames/event map; tidak menyediakan private tuple ke AI/FE |
| `ObservedStateReducer` | `apply(record, state)` → state dengan last/current observations, recorded clearances, runway configuration, coverage | Reducer fixture state dengan same-time/out-of-order events |
| `SessionWriter` | Commit source records, derived analysis frames, command receipts atau assist revisions dalam transaksi sesuai resource | In-memory writer dengan fault injection |

Source events immutable; historical detector frames diarsipkan dengan engine/config/layout version. Detector re-analysis ditandai analysis baru, tidak mengganti rekaman lama. AI `replay_analysis_id` mengacu pada source session immutable dan versi inputs/model/rule/transcript revision yang dibekukan. ID review UI ephemeral tidak menjadi identitas rekaman asal.

Saat membungkus event log current, TRACK/CLEARANCE/READBACK/COORDINATION dan perubahan konfigurasi terstruktur dipetakan sebagai source/session inputs; ALERT_OPEN/ALERT_LEVEL/ALERT_RESOLVED adalah derived transitions. COMMAND receipt tetap control/audit, tidak diterapkan ulang bersamaan dengan resulting CLEARANCE event saat replay historical. Hasil AI dan annotations mempunyai resource/analysis sendiri. Source alerts yang memang diekspor simulator mitra tetap external evidence dengan provenance; tidak diganti menjadi rule output FlowLens atau diberi authority yang sama. Vendor event types yang belum dipetakan menjadi unsupported import records, bukan ditebak dari message text.

Privacy: participant own assessments, instructor/evaluator evidence, dan private truth terpisah. Baseline condition menyembunyikan prediction/explanation sesuai existing Manager. **PROPOSED_CONTRACT:** evaluator MVP memakai instructor-scoped replay access dengan capability `evaluator_only`; role `evaluator` baru tidak ditambahkan ke enum current. Capability diperiksa server, bukan diterima dari client. Ground truth tidak termasuk evidence input model.

## SC-03 — Detector dan lifecycle

CURRENT function di [detection.py](../../backend/detection.py):

```python
detect(tracks, clearances, now_ms, config, runway_open,
       expected_ids, previous_tracks=None) -> dict
```

Output actual `{predictions, candidates, runway}`. Candidate deterministic berbeda dari `AdvisoryOptionCandidate` AI. Candidate memuat `key`, `rule`, `rule_version`, sorted `objects`, `runway`, `severity`, `reason`, `metrics`, `evidence_event_ids`, `calculated_ms`, `track_ages_ms`, `assumptions`, `data_degraded`. `Session.evaluate` menambah lifecycle fields; `detect` tidak menghasilkan final Alert lifecycle.

Prediction actual: `object_id`, `physical_runway_id`, `direction`, `interval_index`, `entry_s`, `exit_s`, `exit_unknown`, `assumed_entry_range_s`, `assumed_exit_range_s`, `threshold_eta_s`, `model_version`, `source_event_id`. Entry/exit adalah detik relatif terhadap calculation time, bukan absolute source timestamp. `exit_unknown=true` tidak boleh disajikan sebagai kepastian runway clear pada horizon.

**PROPOSED_CONTRACT:** `DetectorPort.evaluate(ObservedDetectorInput) -> DetectionResult`; SD memiliki domain DTO di `backend/detection_contracts.py` (belum ada). Input terdiri dari shape Track/Clearance current, `now_ms`, config, runway_open, previous_tracks, explicit public layout, dan expected IDs dari coverage source. Result mempertahankan nama/semantik actual `predictions/candidates/runway`; wrapper adapter tidak mengganti severity.

`AlertLifecyclePort.update(previous_alerts, result, now_ms) -> alerts + transition events` adalah fungsi SD tanpa DB/Session imports; BE memberikan state dan menyimpan output. Dedup sorted objects/rule/physical runway dalam namespace session; acknowledgement tidak resolve, dropout tidak membuktikan clear, downgrade/resolution memerlukan tiga detik simulasi sesuai plan §10.3. Stale threshold baseline `>3000 ms`, horizon `120 s`, tick `100 ms` adalah parameter latihan pada config, bukan standar operasi.

## SC-04 — Audio/job dan worker boundary

Semua tipe berikut `PROPOSED_CONTRACT`, berasal dari minimum addendum §3.4; belum ada di source. AI memiliki payload worker/DTO assist, BE memiliki asset/job storage/transport. Bentuk vendor/provider tidak menjadi kontrak UI.

| Tipe | Field minimum |
|---|---|
| `AudioAsset` | `id`, `session_id` (source session), `source_kind`, `source_ref`, `channel_id`, `audio_start`, `timebase`, `duration_ms`, `hash`, `provenance`, `permission_profile`, `retention_until` |
| `TranscriptionJob` | `id`, `asset_id`, `status`, `provider`, `model`, `version`, `language`, `started_utc`, `finished_utc`, `error`, `chunk_progress` |
| `WorkerRequest` | `job_id`, `attempt_id`, `asset_id`, private local asset reference, fixed model/config version dan time mapping; read-only public replay evidence slice bila diperlukan |
| `WorkerResult` | `job_id`, `attempt_id`, `asset_id`, fixed model/config version, status, segments/entities/candidates atau safe error |

Job wire status mengikuti addendum: `queued|running|needs-review|completed|failed|cancelled`. Queued→running→completed atau needs-review; failure/cancellation terminal pada attempt. Retry baru punya `attempt_id`; stale/duplicate attempt tidak commit dua kali. Human review status tidak disimpulkan dari worker selesai. Timeout/cancelled job menolak late result. Job lifecycle milik server BE; worker tidak mengklaim persistence berhasil.

Worker menerima referensi lokal privat yang telah divalidasi, tidak filesystem path bebas dari browser; audio di luar static directory. Worker tidak mempunyai Archive/SQLite writer, command client, token operator atau production feed. Inferensi di proses terpisah; IPC/internal queue typed, server memvalidasi hash/scope/version/evidence lalu menjadi satu writer. Progress tidak memakai simulation clock; replay pause tidak menghentikan wall-clock job timeout.

## SC-05 — Transcript, evidence reconciliation, options, review

**PROPOSED_CONTRACT:** JSON snake_case, extra fields forbidden, nullable confidence berarti unavailable (bukan nol). Confidence bukan severity dan belum dianggap calibrated. ASR source dan reviewer revision tetap dapat ditelusuri.

| Tipe / owner AI | Field minimum dan aturan |
|---|---|
| `TranscriptSegment` | `id`, `asset_id`, `start_ms`, `end_ms`, `channel_id`, `speaker_label`, `speaker_source`, `speaker_confidence`, `text`, `language`, `asr_confidence`, `model_version`, `correction_status`; start/end dalam audio-relative ms, map ke session lewat asset timebase |
| `CandidateEntity` | `segment_id`, `entity_type`, `candidate_value`, `normalized_value`, `confidence`, `alternatives`; types callsign/runway/instruction/number/negation/time/actor/channel sesuai addendum |
| `AssistHighlight` | `id`, `category`, `review_priority`, `statement`, `transcript_segment_ids`, `session_event_ids`, `uncertainty`, provider/rule version, `status`; optional `linked_alert_id` dan `link_status` hanya bila relevan |
| `AdvisoryOptionCandidate` | `id`, `replay_analysis_id`, `option_statement`, `rationale`, `supporting_evidence_ids`, `preconditions`, `unknowns`, source/model/rule version, review status; applicability limitations ditulis dalam preconditions/unknowns |
| `ReviewAnnotation` | `target_id`, `decision`, `reviewer`, `timestamp`, `correction` atau `reason`; decision `corrected`, `confirmed`, `dismissed`, atau `unresolved`; reviewer/time dari server |

`EvidenceReader.resolve(refs, source_session_id, analysis_scope)` mengembalikan public event/segment/alert/version atau unresolved reference. Untuk `supporting_evidence_ids`, **PROPOSED_CONTRACT** gunakan refs bertipe `{kind: session_event|transcript_segment|detector_alert, id}`. Ini menghindari string ID ambigu; tidak mengubah arrays IDs existing deterministic alert/highlight. Setiap fakta pada rationale harus bisa dipetakan ke refs; validator memastikan referensi ada dalam scope, sedangkan dukungan makna tetap perlu evaluasi. Referential integrity bukan bukti kebenaran model.

Hubungan shared event/entity yang jelas dapat `linked`; kedekatan waktu saja `possible_link`, tidak auto-merge. Candidate yang berkaitan dengan alert existing tampil sebagai annotation pada evidence panel, tidak menduplikasi hazard/severity. Missing clearance event pada log terbatas tidak membuktikan clearance tidak pernah diberikan.

Option hanya untuk analysis atas replay immutable dan evaluator context. Schema tidak memuat `command`, `clearance`, `instruction_action`, `control_action`, atau payload eksekusi. Tidak ada callback yang mengirim option ke `Session.execute`. Nilai entity `instruction` adalah hipotesis ucapan, bukan objek Clearance. Raw/model text diperlakukan data, tidak dieksekusi sebagai prompt/tool instruction.

Review annotations append-only mempunyai ID/revision storage server; `correction` menunjuk target dan basis revision supaya update stale ditolak, raw text tidak ditimpa. Confirm/dismiss adalah keputusan review candidate, tidak mengubah structured simulator event atau deterministic severity. Detail HTTP request correction dan storage revision berada pada SC-06; tidak gunakan `Assessment` current sebagai pengganti lengkap audit transcript.

## SC-06 — REST/stream compatibility dan tambahan

Owner transport BE; FE memakai satu adapter. Semua rows CURRENT di bawah diperiksa pada [app.py](../../backend/app.py); tidak diverifikasi runtime.

| CURRENT_SOURCE route | Request/response penting |
|---|---|
| `GET /health` | `{status, version, mode: synthetic-training, single_writer}`; bukan readiness ASR |
| `POST /api/v1/auth/operator` | `{key}` → `{token, expires_in_s}` |
| `GET /api/v1/scenarios[/{id}]` | Collection `{items}` atau public Scenario |
| `GET/POST /api/v1/sessions` | List `{items}`; CreateSession → metadata dengan HTTP 201 |
| `GET /api/v1/sessions/{id}` | Metadata; review memakai `{id, kind, source_id, status}` |
| `POST .../{id}/seats` | `{role, label}` → `{token, session_id, role, label, expires_in_s}` |
| `GET .../{id}/snapshot` | Full authorized snapshot SC-02 |
| `POST .../{id}/commands` | `Command` dari models: `command_id`, `expected_revision`, `type`, optional `target`, `instruction`, `runway`, `value`, `readback`; response session/revision/status, training juga command_id |
| `GET .../{id}/events?cursor=&limit=` | `{items, next_cursor}`; limit current 1–500, default 100; cursor ordinal, bukan time/sequence |
| `POST .../{id}/reviews` | Source frozen → `{id, source_id, token}`; body tidak diperlukan |
| `POST .../{id}/branches` | `{at_ms}` → `{id, parent, token}`; perlu private compatible synthetic checkpoint |
| `POST .../{id}/acknowledgements` | `{alert_id}`; tidak resolve |
| `POST .../{id}/assessments` | `{type, text, values}`; review annotations current in-memory |
| `GET .../{id}/report?format=json\|csv\|html` | Instructor-only; JSON current termasuk truth, jangan diberikan ke AI/participant |
| `WS .../{id}/stream` | Auth message pertama `{token}` dalam 5 s; direct snapshots setiap 0.2 s; scope/expiry server |

Command review `SEEK.value` dalam **detik**, branch `at_ms` dalam **ms**. `SET_SPEED.value` current `0.5|1|2|4`. Actor dari token; client tidak mengirim actor untuk menambah authority. Idempotency current command_id+payload+actor, stale revision 409. Error current FastAPI `{detail: ...}`, bukan envelope `code/message/request_id` target. FE adapter mengakomodasi detail string/validation list; tidak mengklaim stable error code sudah ada.

### PROPOSED_CONTRACT: additive replay/assist profile

| Route usulan / access | Request minimum | Response / consumer |
|---|---|---|
| `POST /api/v1/replay-imports` / operator/instructor | Local validated export upload + SC-01 manifest; transport multipart detail milik BE | `{source_session_id, source_id, import_status}`; tidak mengubah `POST sessions` synthetic |
| `GET /api/v1/sessions/{id}/replay-source` / scoped review | None | Manifest public projection + source session identity; permission references, tanpa private path |
| `POST .../{id}/audio-assets` / instructor | Local file + AudioAsset import metadata SC-04; server menetapkan id/hash | `{asset, job}`; hanya source replay, file validation sebelum queue |
| `GET .../{id}/transcription-jobs/{job_id}` | None | TranscriptionJob, progress/error aman |
| `GET .../{id}/transcripts?cursor=&until_ms=` | Audio/segment cursor opak; until_ms dalam session time | `{items, next_cursor}`; immutable segments + revisions scoped |
| `POST .../{id}/transcripts/{segment_id}/corrections` / reviewer | `{request_id, expected_revision, text, reason}` | Append-only revision + ReviewAnnotation |
| `GET .../{id}/highlights` dan `POST .../{id}/highlights/{highlight_id}/review` | Review `{request_id, expected_revision, decision, reason}` | Scoped candidates atau append-only annotation |
| `GET .../{id}/replay-analyses/{analysis_id}/options` / evaluator-only replay | None | `{items}` AdvisoryOptionCandidate; analysis immutable source/version binding |
| `POST .../{id}/replay-analyses/{analysis_id}/options/{option_id}/review` / evaluator-only | Review shape di atas | Append-only review; tidak ada execute endpoint |
| `WS .../{id}/assist-stream` / scoped replay | First message auth `{token}` | Typed messages di bawah; URL sama sebagai HTTP upgrade, bukan REST GET JSON |

`id` routes assist mengacu source session immutable; bila FE sedang memakai ephemeral Review ID, adapter menggunakan `source_session_id` dan access token yang memiliki source scope, bukan otomatis memakai review token untuk source. BE dapat memberikan scoped source-read credential/capability saat create review tanpa memperluas command rights. Policy capability/expiry harus diuji; current token review sendiri tidak mengizinkan source lookup.

Assist transport envelope minimum usulan:

```typescript
type AssistMessage = {
  schema_version: 'assist-1'; source_session_id: string;
  sequence: number; type: 'snapshot' | 'job_progress' | 'segment' |
    'highlight' | 'option' | 'review_annotation' | 'error';
  payload: unknown; // discriminated DTO menurut type, divalidasi sebelum adapter
}
```

Pada implementasi, `payload` wajib union DTO, bukan `unknown` di page. Initial/reconnect assist stream mengirim full authorized assist snapshot; gap sequence menyebabkan resync. Sequence assist terpisah dari snapshot source. `until_ms`/scope menghindari event atau transcript masa depan pada tampilan historical; full-session analysis boleh diproses offline, tetapi tidak masuk view earlier-time tanpa label analysis window. Main stream current tidak berubah. Option tidak disiarkan ke training seats.

Corrections/reviews usulan idempotent terhadap `request_id`+normalized body+actor; 409 untuk collision/stale revision. Backend memeriksa target/source relation sebelum commit. HTTP failures mengikuti status existing 401/403/404/409/422; service unavailable terlapor 503 tanpa sukses persistence palsu. Provider failure dapat menjadi status job failed dengan source replay tetap tersedia. Tidak memaksakan envelope global baru ke API lama.

## SC-07 — Typed frontend port dan read model

Owner FE. **PROPOSED_CONTRACT** `ReplayReviewAdapter` menyediakan `loadSource`, `loadFrame(at_ms)`, `listEvents(cursor, until_ms)`, `listTranscript(cursor, until_ms)`, `resolveEvidence(refs)`, `listCandidates(analysis_id)`, `subscribeSource`, `subscribeAssist`, `controlReview`, `correctTranscript`, `reviewCandidate`. Fixture dan API adapters mempunyai interface sama. Auth/scope, serialisasi, unit SEEK, event pagination, runtime decoding, cancellation, serta reconnect berada di adapter, tidak di page.

Read model minimum: source identity/label/versions, frame/time (`sim_ms` versus requested/playback time), layout, observed tracks/quality, clearances, deterministic predictions/alerts, ordered timeline, transcript with raw/corrected revision, highlights/options/evidence links, viewer capabilities, connection/job state. Public projection tidak memuat checkpoint/RNG/private future actions/truth.

UI state union: `loading|empty|ready|degraded|disconnected|unauthorized|conflict|error`; job disabled/unavailable dan analysis unknown disajikan per panel. Data source tidak berganti ke fixture ketika network gagal. Historical frame masih boleh ditampilkan dengan disconnected badge; tidak extrapolate sebagai observed truth. Frontend tidak menghitung ulang severity atau confidence AI.

## Versioning dan compatibility

CURRENT versions `ENGINE_VERSION=0.1.0`, `CONFIG_VERSION=lab-sop-1`, scenario/layout `1.0` bukan schema stream version. `replay-1`/`assist-1` adalah version profile **usulan**, bukan klaim server current. Unknown major/profile ditolak sebagai unsupported. Perubahan additive tetap memerlukan schema/fixture parity; jangan mengandalkan FE cast atau menonaktifkan extra-forbid. Field rename/unit change memerlukan version baru/adapter eksplisit. Archived data dibaca memakai versi historis; incompatible private checkpoint melarang branch tetapi tidak public review.

## Contoh fixture minimum lintas paket

Semua contoh berikut authored synthetic, bukan hasil runtime. QA kelak menyimpan fixture files; blueprint ini hanya menyediakan isi/aturan referensi.

```json
{
  "id": "SYN-01:2", "ordinal": 2, "sim_ms": 500,
  "audit_utc": 0, "type": "TRACK", "message": "Synthetic observed track.",
  "target": "ARFF-2", "observed_ms": 0, "received_ms": 500,
  "track": {
    "id": "ARFF-2", "callsign": "ARFF-2", "kind": "vehicle",
    "x_m": 1500, "y_m": -110, "speed_mps": 0, "heading_deg": 90,
    "phase": "holding", "length_m": 12, "width_m": 3,
    "runway": "27", "route": [[1500,260]], "owner": "ground",
    "observed_ms": 0, "received_ms": 500,
    "source": "simulated-surface", "event_id": "SYN-01:2"
  }
}
```

Clearance paired event `SYN-01:1` ordinal 1 pada sim_ms 0: `type=CLEARANCE`, target ARFF-2, instruction HOLD_SHORT, runway 27, issuer scenario. Clearance object `event_id=SYN-01:1`; initial state source scope hanya ARFF-2, tanpa ground truth. At sim_ms 3000 track belum stale; at 3001 stale. Fixed times ini oracle aging baseline, bukan measured output. Test initial missing di 0–499, nominal setelah 500, dan paused age tidak bertambah.

Untuk assist fixture SYN-COMM-01 gunakan [addendum §5](../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md#5-paket-data-demo-mendekati-workflow-nyata): segment `SEG-TWR-006`, clearance `EVT-CLR-021`, observed track `EVT-TRK-088`, deterministic alert `ALRT-009`. Manifest menyatakan source timestamps/offset; receipt track harus 350 ms setelah observed timestamp (bukan mengganti keduanya). Highlight tidak mempunyai control_action field. Analisis `AN-SYN-01` hanya menunjuk source immutable.

```json
{
  "id": "OPT-SYN-01", "replay_analysis_id": "AN-SYN-01",
  "option_statement": "Evaluator memeriksa ulang segmen dan alignment event sebelum menilai urutannya.",
  "rationale": "Segmen ambigu dan event HOLD_SHORT memerlukan pemeriksaan bukti pada replay.",
  "supporting_evidence_ids": [
    {"kind": "transcript_segment", "id": "SEG-TWR-006"},
    {"kind": "session_event", "id": "EVT-CLR-021"}
  ],
  "preconditions": ["Replay offline; akses evaluator pada source yang sama."],
  "unknowns": ["Negasi pada segmen belum dapat dipastikan; alignment perlu diperiksa."],
  "source_version": "synthetic-fixture-1", "model_version": "stub-1",
  "rule_version": "reconcile-fixture-1", "review_status": "unresolved"
}
```

Bundle minimum QA meliputi manifest/geometry, source events, public historical frames, asset metadata + synthetic audio atau transcript stub eksplisit, raw segments/revisions, highlights/options, independent expected outputs dan private evaluator labels terpisah. Variants: missing/stale, duplicate/out-of-order, alignment unknown, invalid reference/extra action field, cancelled/late worker, unauthorized source, seek antara frames, assist reconnect gap. Tidak boleh stub transcript dilabeli output ASR nyata.
