# BE — Backend/session/replay/storage

**Owner-role:** Backend/Replay. **Status:** packet TARGET dengan interface `PROPOSED_CONTRACT`; baseline `CURRENT_SOURCE` diperiksa statis pada 3 Oktober 2026. [Master](../README.md) · [Shared contracts](../shared-contracts.md).

## Objective dan output

Menyediakan satu pemilik state/persistence yang menerima export replay offline, menyimpan source immutable serta derived results terpisah, dan melayani replay/review terotorisasi tanpa menunggu detector/AI/UI selesai.

Deliverables implementasi: source import validator/adapter, immutable replay archive/read service, injected detector/lifecycle/worker ports, persistence asset/job/analysis/reviewer revisions, API/stream additive, dan serializer public yang kompatibel. Consumer SD menerima state/config/layout, AI menerima read-only evidence dan validated job, FE menerima typed API/read models, QA menerima port adapters untuk contract/integration checks.

## CURRENT/TARGET dan scope

| Label | Kondisi |
|---|---|
| CURRENT_SOURCE | FastAPI `create_app`, Manager lock/clock/token access; Session hard-wired Simulator, detect dan Archive; Review membaca frozen public frames; Archive SQLite empat tabel; report JSON menyertakan evaluator truth |
| TARGET | Source import offline di samping synthetic sessions, versioned provenance/timebase/coverage, archive source versus analyses, durable corrections/reviews, scoped read API/assist stream |
| UNKNOWN | Format export/audio mitra, clock drift, izin/retensi/lokasi pemrosesan, compatibility checkpoint vendor, storage volume dan hardware |

Included: local/LAN single process/server writer, import/read/replay control, consistency/receipts, privacy redaction, asset/job metadata, durable worker result commit dan annotations. Excluded: inferensi model, perubahan geometry/rule semantics, UI rendering, live feeds/audio, clearance dari AI, vendor adapter spekulatif dan internet hosting. Branch hanya synthetic checkpoint compatible; imported partner replay tanpa private checkpoint tetap read-only.

## Context packet

| Baca | Relevansi |
|---|---|
| [app.py](../../../backend/app.py) | Routes, scopes, lock, startup, stream/auth, static UI |
| [session.py](../../../backend/session.py) | Event/revision/sequence, observed state, lifecycle glue, atomic save/error dan branch restore |
| [storage.py](../../../backend/storage.py), [review.py](../../../backend/review.py) | Frame/event queries, private checkpoint, immutable review control, current in-memory annotations |
| [models.py](../../../backend/models.py), [reporting.py](../../../backend/reporting.py) | Current request models, versions, exports/redaction boundary |
| [pyproject.toml](../../../pyproject.toml) | Python dependencies/config; tests directory target belum ada |
| [Plan](../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md) §6–8, §13–14, §16.2 | Single writer, data/time, API, atomic storage, recovery |
| [AI addendum](../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md) §3.1, §3.4–3.5 | Worker ownership, assets/jobs/review, additive routes |

Tidak ada test backend yang ditemukan; daftar verification di bawah adalah pekerjaan implementasi. Source SD hanya dibaca untuk signature SC-03; BE tidak mengambil alih rule body.

## Modul/file ownership

BE sendiri mengubah `backend/app.py`, `session.py`, `storage.py`, `review.py`, `reporting.py`, `models.py`, `__init__.py`, `pyproject.toml` bila perlu. File baru usulan: `backend/replay_contracts.py` (SC-01/02 DTO), `backend/ports.py` (injection boundaries), `backend/replay_import.py` (manifest/record validation), `backend/replay_source.py` (import archive reader), `backend/assist_service.py` (jobs/review authorization), `backend/assist_storage.py` (asset/analysis/revisions persistence).

SD memiliki `DetectorPort`/lifecycle domain implementations; BE mengganti panggilan hard-wired di Session dengan injection. AI memiliki `assist_contracts.py` dan worker/provider code; BE mengimpor DTO untuk storage/transport, bukan menulis ulang. Domain DTO tidak mengimpor service BE. Runtime registration di composition root `app.py`; tidak membuat AI provider mengakses `Archive`.

Session initialization current membuat initial synthetic clearances/truth dan langsung save. Imported replay **tidak** boleh memakai constructor itu tanpa pemisahan source mode: jangan menambahkan BAW123/ARFF-2/initial clearances ke source vendor. SC-02 `ReplayEventSource` memungkinkan reducer/read service mulai mandiri, sambil mempertahankan `POST sessions` existing.

## Inputs, outputs, kontrak dan consumer

| Input/operasi | Output | Kontrak / consumer |
|---|---|---|
| Export file + manifest | Validated immutable source records atau import errors | SC-01; state reducer, QA |
| Source records pada receive time | Observed state + previous observations/coverage | SC-02/03; SD |
| DetectionResult + previous alerts | Derived frames/transitions tersimpan | SC-03; FE historical replay, AI evidence reader |
| Audio import + model config | Validated asset, queued job, WorkerRequest | SC-04; AI worker |
| WorkerResult | Validated assist output/analysis version dan progress | SC-04/05; FE evaluator, QA |
| Correction/review request | Append-only revision/annotation dan receipt | SC-05/06; reviewer/debrief |
| Authenticated read/control | Authorized snapshot/history/stream atau safe error | SC-02/06; FE adapter |

SC-06 merupakan satu daftar route/wire; packet ini tidak mengganti auth route atau command fields existing. New source import/assist endpoints additive. Stable source session dan ephemeral review ID dibedakan; adapter/capability source-read ketika membuat review mencegah penggunaan token scope yang salah.

## Mock/stub/fixture untuk pengerjaan mandiri

- `FixtureEventSource`: manifest `synthetic`, ordered events dengan receive/sample timestamps, track fields current, frame pada 0/200/400 ms; immutable bytes/hash fixture. Tidak perlu Simulator riil.
- `StubDetector` dan `StubLifecycle`: memberi DetectionResult/transition yang diketahui dan bisa gagal secara eksplisit; tidak mengklaim output stub perhitungan domain.
- `StubWorker`: queued/running/result, timeout/cancel, duplicate attempt, invalid evidence/extra action field; input asset synthetic kecil atau transcript fixture dengan label stub.
- `InMemoryArchive/Writer`: implementasi port dengan commit failure injection; persistence unit BE dapat memakai SQLite sementara setelah implementasi tersedia.
- Auth fixture instructor/source-bound/observer/expired/cross-source; baseline redaction fixture dan review credential source-read. Jangan embed operator key asli dalam fixture.

QA memiliki fixture canonical; BE dapat membuat fixture lokal unit sendiri di memory. Tidak menunggu fixture file QA untuk menyelesaikan service against kontrak yang sama.

## Alur utama

1. Validasi manifest/asset scope, file hash/type dan semua records ke staging privat. Tolak unsupported mapping/unit/layout/nonfinite input; duplicate identical source IDs dedup, conflicting ID menjadi import conflict. Incomplete source disimpan sebagai unknown/degraded, tidak diberi authorized label tanpa metadata penggunaan.
2. Persist source metadata+records atomik sebelum visible `import_status=completed`. Record external identity/source time sidecar dan normalized IDs/time. Import gagal tidak meninggalkan half-readable session.
3. Untuk re-analysis, reducer membaca records sampai requested receive time; previous/current state tidak mundur karena late sample. Inject SD port dan public layout; simpan analysis/version output terpisah. Historical review cukup membaca archived frames, tidak wajib rerun detector/model.
4. Register audio hanya ke source replay. Buat immutable private asset, hash/mapping dan job receipt; dispatch worker tanpa memegang clock lock selama inference. Server menjalankan finite schema/scope/evidence validation atas result dan menyimpan satu kali per attempt.
5. Serve source and assist streams separately. Filter evidence/segments di view time dan authorization; analysis window yang lebih luas ditandai. Raw model output tidak langsung menjadi public snapshot.
6. Koreksi/decision menambah annotation/revision dengan author/time server dan expected revision. Debrief/export merujuk source versions/raw result/revisions dan label synthetic/authorized; report truth tetap evaluator-only.

## Failure/degraded cases

| Trigger | Perilaku wajib / batas current |
|---|---|
| Missing time/coverage/route | Unknown/degraded; jangan isi zero/fresh atau runway clear |
| Import invalid/partial/hash berubah | Safe validation failure; staged input tidak mengganti committed source |
| Disk failure | Tidak mengembalikan saved/success; source committed tetap readable bila storage tersedia; training dipause sesuai target |
| Mutation terjadi sebelum `Session.save` gagal | Current tidak menunjukkan rollback memory penuh; implementasi harus restore committed state/recovery, lalu uji command retry tidak menggandakan efek |
| Restart | Current Archive menandai READY/PAUSED/RUNNING INTERRUPTED; no auto-resume; read committed source dan durable receipts |
| Review/annotation setelah restart | Current Review dan annotations in-memory hilang; target durable assist revisions harus terpisah dan diuji |
| Worker timeout/cancel/late duplicate | Job failure/cancel state, result rejected atau dedup; replay/detector tidak bergantung pada AI health |
| Evidence/correction cross-source atau stale revision | 403/404 scope failure atau 409 conflict; raw result tidak berubah |
| Frame seek/checkpoint incompatible | Frame terakhir <= target; return actual frame time; branch unavailable tanpa menghalangi review |
| Main WS/assist WS disconnect | Resync full authorized snapshot; sequences domain berbeda; expiry tetap wall time |

Archive current menyimpan frame berdasarkan `(session_id, sim_ms)` dan replaces same-time frame. TARGET harus menjelaskan snapshot revision yang dibaca; same-time event ordering tetap ordinal. Event paging current memilih limit lalu time-filter; QA harus menguji seek lalu pagination, terutama same-time rows, agar cursor tidak menampilkan future events.

## Verification teknis / readiness-to-integrate

Hasil siap dihubungkan bila implementasi menunjukkan:

1. Manifest/record fixtures round-trip dengan source ID/time/unit/hash/version utuh; invalid source/time/nonfinite ditolak; duplicates/out-of-order tidak memundurkan latest observed state.
2. Import tidak membuat initial synthetic objects/clearances; private truth/future schedule/checkpoints tidak ada dalam read/stream atau worker payload.
3. Current command route/fields dan auth/stream first-message tetap kompatibel; same command ID/payload/actor satu efek, different payload/actor conflict; retry sesudah commit failure memakai committed receipt/state.
4. Seek/review memakai source historical frame/config/time; source hash/events tidak berubah oleh controls/corrections/options; branch kompatibilitas diuji hanya pada synthetic private checkpoints.
5. Worker attempt cancellation/timeout/duplicate/invalid output terisolasi; result valid committed sekali; corrections append-only dan durable sesudah restart.
6. Negative scope/expiry/baseline/redaction checks dilakukan server; replay token tidak memperoleh source access implisit; instructor capability khusus evaluator tidak menambah command path option.
7. SQLite temporary-file recovery/storage fault checks dan REST/WS contract tests lulus dengan stubs sebelum full SD/AI runtime; kemudian integration dengan implementation riil sesuai [QA](integration-qa.md).

Ini readiness teknis, bukan approval/sign-off. Semua checks di atas belum dijalankan oleh tugas dokumentasi.

## Asumsi dan unknown

**ASSUMPTION:** profile normalized offline `replay-1`, same-host worker queue/IPC dan SQLite disk lokal cukup untuk baseline, tanpa Redis/cloud. Single RUNNING target; source guard multi-session tidak menjadi tuntutan concurrency tambahan.

**UNKNOWN:** vendor data shape/clock alignment/coverage, permission metadata nyata, retention policy dan audio volume; model config/hardware supplied AI packet; migration/backup/version-reader detail perlu implementasi BE. Role evaluator khusus belum ada; usulan capability instructor replay memenuhi mock tanpa mengarang role enum current.
