# Rencana Eksekusi Paket A — Platform & Replay

Tanggal: 9 Oktober 2026. Owner: pengguna sebagai Pihak A. A01 `done`: A01.1–A01.3 `done`; A02 `done` (A02.1–A02.2 done); A03 `done` (A03.1–A03.3 done); A04 `done` (A04.1–A04.3 done); A05 `done`; A06 `done`; A07 `in_progress` (A07.1 done; A07.2–A07.3 planned); A08–A10 `planned`. Baseline bersama: contract 1.0.0, Phase 0–1 selesai. Evidence: [A01.1](../testing/a011-evidence.md), [A01.2](../testing/a012-evidence.md), [A01.3](../testing/a013-evidence.md).

## Pendekatan dan scope

Paket A dibagi menjadi 10 tahap dengan 26 unit sesi. Kerjakan satu unit sesi per permintaan; verifikasi dan simpan handoff sebelum melanjutkan. Nomor A01–A10 adalah rincian eksekusi dari roadmap yang ada, bukan pengganti nomor Phase 2–10.

Scope mencakup host, persistence/transaksi, identity/authorization, import/source/clock, assets/evidence, jobs, replay/transport, geometry/rules, artifact lifecycle/retention, serta platform ops. Implementasi B, provider inference, frontend, containerization dan deployment tetap mengikuti paket/gate masing-masing. Paket A memakai fake analysis melalui ports sampai integrasi Phase 10.

Urutan rekomendasi: A01 → A02 → A03 → A04 → A05 → A06 → A07 → A08 → A09 → A10. Urutan ini mengurangi perpindahan konteks; mapping ke roadmap tetap menjadi otoritas scope. Setelah fondasi selesai, jobs secara arsitektur tidak perlu menunggu replay/geometri.

## Checklist tahap

- [x] A01: Bangun host, persistence dan migrations platform — Phase 2.1.
- [x] A02: Bangun lifecycle akun dan autentikasi — Phase 2.2.
- [x] A03: Terapkan grants, transport policy, audit dan mutation consistency — Phase 2.3–2.4.
- [x] A04: Bangun import/provenance/clock dan commit atomik — Phase 3.1–3.4.
- [x] A05: Bangun akses aset privat dan registry evidence — Phase 6.1 serta boundary evidence Paket A.
- [x] A06: Bangun durable jobs dan accepted-result coordinator — Phase 6.3.
- [ ] A07: Bangun replay deterministik, controls, REST dan WebSocket — Phase 4.1–4.4.
- [ ] A08: Bangun geometry, occupancy, rules dan alert lifecycle — Phase 5.1–5.4.
- [ ] A09: Bangun artifacts, retention/purge dan platform ops/recovery — bagian A Phase 9.4/9.6.
- [ ] A10: Verifikasi acceptance mandiri dan serahkan manifest Paket A — persiapan entry Phase 10.

## A01 — Host, SQLite dan migrations

**Prasyarat:** baseline 1.0.0 dan [ownership platform/analysis](../architecture/backend-baseline.md).

Progress: A01.1–A01.3/A01 `done`; A03–A06 juga done. Audited legacy archive conversion tersedia; legacy credentials/routes tetap deprecated, public compatibility readers tetap A07.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A01.1 | Buat host/composition A dan validasi config; gunakan registry/ports frozen dengan fake B pada test profile | Startup/config checks; single API writer; safe errors; profile mandiri tidak mengklaim production readiness |
| A01.2 | Buat migration runner, schema platform, repositories dan UOW; pertahankan namespace analysis milik B | Fresh/upgrade, FK/unique constraints, migration dependency/checksum policy, commit/rollback dan callback setelah commit |
| A01.3 | Audit format archive/operator-key historis melalui Git; tetapkan compatibility/deprecation dan implementasikan migration yang diperlukan | Fixture archive representatif; IDs/events/frames/commands dipertahankan; unsupported input ditolak secara eksplisit |

Jangan memakai `flowlens.testing.SQLiteHarness` sebagai storage aplikasi. Jangan mengarang format archive lama dari reference schema. Bila format belum terbukti, catat gap acceptance dan lanjutkan pekerjaan independen; A01 belum seluruhnya `done`.

## A02 — Akun dan autentikasi

**Prasyarat:** A01.1–A01.2.

Progress: A02.1–A02.2/A02 done ([accounts](../testing/a021-evidence.md), [HTTP sessions](../testing/a022-evidence.md)); A03–A06 juga done. [Account/CLI workflow](account-lifecycle.md) menjelaskan trusted internal boundary dan session revocation yang terhubung ke transport policy; stream scheduling nyata tetap A07.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A02.1 | Bangun account repository, Argon2id, bootstrap admin dan reset/deactivation | Tidak ada default password publik; hash dan secret tidak bocor; reset/deactivation membatalkan akses terkait |
| A02.2 | Bangun login/logout, cookie sessions, expiry dan rate limiting | Login sukses/gagal, logout, expired/revoked session dan rate-limit tests; attributes cookie sesuai konfigurasi |

Account tidak disamakan dengan seat/position. Argon2 dependency ditambahkan melalui manifest/lock dengan verifikasi kompatibilitas, bukan versi tebakan.

## A03 — Authorization dan konsistensi mutations

**Prasyarat:** A02; operasi domain yang belum tersedia memakai test services melalui ports.

Progress: A03.1 `done` ([evidence](../testing/a031-evidence.md), [authorization workflow](authorization.md)); A03.2 `done` ([evidence](../testing/a032-evidence.md), [transport workflow](transport-policy.md)); A03.3 `done` ([evidence](../testing/a033-evidence.md), [mutation workflow](mutation-consistency.md)); A03/Phase2 `done`; A04–A06 juga done.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A03.1 | Bangun grants/capabilities dan server-built RequestContext; pisahkan session/raw audio/export/truth; siapkan internal worker principal | Cross-session/run denial, grant expiry/revocation, admin tanpa grant, least-scope worker; context dari klien tidak dipercaya |
| A03.2 | Terapkan CSRF dan HTTP/WS origin/session policy serta serializers sesuai role | Negative CSRF/origin/principal tests; truth/secret/private path tidak masuk public DTO |
| A03.3 | Bangun audit append-only, optimistic version dan durable idempotency infrastructure | Same key/payload satu efek; changed payload/version conflict; rollback mencakup audit/receipt/event; tidak ada success palsu |

Uji policy WS sekarang, lalu uji koneksi WS nyata dan revocation saat stream dibangun pada A07.3. Authorization media/export juga diuji kembali pada route nyata A05/A09.

## A04 — Import, provenance dan clock

**Prasyarat:** A01–A03; gunakan fixture sintetik baseline.

Progress: A04.1–A04.3/A04 `done` ([phase evidence](../testing/a04-evidence.md), [commit/source workflow](import-commit.md)); A05/A06 juga done. Draft preview belum committed; explicit commit kini tersedia. No integrasi B.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A04.1 | Bangun private upload staging, size/content/duration/path/hash validation dan preview/remediation | Malformed/oversized/traversal/nonfinite ditolak; belum ada sesi committed pada preview |
| A04.2 | Bangun manifest/rights/retention/coverage dan normalisasi clock/timezone/identity/units/layout | Manifest/hash round-trip; local/cloud/export rights terpisah; unknown alignment/coverage tetap unknown; independent time oracle |
| A04.3 | Bangun commit import, dedup/conflict dan source reader melalui ports | Audio-only dan paired input; raw immutable; fault injection tidak meninggalkan sesi half-readable; truth/private schedule tidak masuk worker input |

DB dan filesystem tidak memiliki transaksi atomik bersama: dokumentasikan staging/promotion, recovery dan orphan cleanup, lalu uji crash pada batas tersebut. Audit pronunciation/time mapping fixture audio sesuai acceptance Phase 3; script TTS tidak otomatis gold transcript. Cloud permission enforcement diuji tanpa provider call, lalu diperiksa ulang pada lease/result A06.

## A05 — Aset privat dan evidence

Progress: `done`; [workflow](private-assets-evidence.md), [phase evidence](../testing/a05-evidence.md).

**Prasyarat:** A03–A04.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A05.1 | Bangun private storage keys, authorized audio download/range dan akses worker minimal | Range valid/invalid, denied/revoked access, hash utuh, private path tidak bocor; worker tidak memperoleh seluruh inventory |
| A05.2 | Bangun evidence registry/resolve/register dengan UOW | Scope session/run/revision, source hash, quote/span/audio/event range dan as-of diverifikasi; unavailable evidence eksplisit; registry rollback atomik |

Semantik interpretasi evidence milik B; A memverifikasi sumber, referensi, range, scope dan akses. Decode/resample/chunk FFmpeg tetap milik B.

## A06 — Jobs dan accepted results

Progress: `done`; [workflow](durable-jobs.md), [phase evidence](../testing/a06-evidence.md). A07.1 done; A07.2 next.

**Prasyarat:** A01–A05. Gunakan `AnalysisModule` fake dan handlers terdaftar; tidak mengimpor internals B.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A06.1 | Bangun runs/jobs/attempts, lease/heartbeat, deadline, retry/cancel, concurrency dan budget reservation | Restart/crash recovery; expired/cancelled leases; race dua claimant; release reservation; internal auth dan input minimal |
| A06.2 | Bangun coordinator validasi dan commit result melalui satu UOW | Check rights/revision/config/run/deadline/budget; domain/evidence/audit/receipt/event satu transaksi; duplicate receipt stabil; late/stale result ditolak; publication failure dapat resync |

Provider call tidak berlangsung dalam replay/DB lock. Exactly-once local commit tidak menjamin exactly-once provider billing. Worker process dan SDK adapters bukan deliverable A.

## A07 — Replay, REST dan WebSocket

Progress: A07.1 `done` ([evidence](../testing/a071-evidence.md), [workflow](replay.md)); A07.2–A07.3 planned.

**Prasyarat:** A01–A05. Snapshot/events analisis masih melalui fake B.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A07.1 | Bangun event source/reducer, deterministic ordering, checkpoints dan AS_KNOWN/DEBRIEF snapshots | Same input/version → same snapshot; future/unknown availability terfilter; independent time oracle; rebuild/checkpoint equivalence |
| A07.2 | Bangun play/pause/seek/step/speed dan leader/follow/local-view; archive/restart/compatibility | Seek tidak memanggil provider; source immutable; control/version conflicts; restart; disposition training routes dan casing historis diuji |
| A07.3 | Bangun catalogue/source/history REST, pagination dan typed WS sequence/snapshot/resync | Same-time page boundaries; reconnect/gap/retry tidak duplicate state; grant revoke/expiry memutus stream; cross-session/origin denial |

Replay test memakai input observed, tanpa evaluator schedule/labels. Training command yang dipertahankan berada pada boundary latihan dan bukan tool AI.

## A08 — Geometri, occupancy dan rules

**Prasyarat:** A07; baca oracle/protocol evaluasi sebelum menulis perhitungan.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A08.1 | Bangun footprint transforms, runway/hold-line/protection dan swept movement | Independent numeric oracle; units/heading/coordinates/boundary cases; footprint bukan center-distance |
| A08.2 | Bangun observed/predicted occupancy intervals, ETA/exit, margins dan eligibility | Speed nol/dropout/stale/coverage gaps mempertahankan uncertainty; missing clock/layout/identity → NOT_EVALUABLE; crossing/arrival shared resource |
| A08.3 | Bangun observed-only rules, evidence/version/severity, alerts/ack dan experimental indicators | S01–S10 dengan oracle independen; cancellation/go-around tidak otomatis clear; reproducible alert transitions; source alert authority; indikator bukan diagnosis workload |

S01–S10 dijalankan pada A08; duplicate commands dan seek/reconnect S11–S12 juga tercakup pada A03/A07/A10. Semantic finding assembly, intent dan memory tetap milik B.

## A09 — Artifacts, retention dan ops/recovery

**Prasyarat:** A01–A08; sensitive inventory/purge dan provider diagnostics B memakai callbacks fake terdaftar.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A09.1 | Bangun artifact submission/promotion/download/expiry, retention/purge coordinator, tombstones dan audit queries | Permissions/export rights, path/hash/partial promotion, expired access, purge retry/inventory dan callbacks; tidak resurrect setelah restore |
| A09.2 | Bangun health/ready/release, sanitized logs, usage/budget aggregation, provider admin profiles dan disk checks | Readiness menunjukkan dependency nyata; no secret/transcript leak; admin authorization; fake diagnostics tidak diberi label provider verified |
| A09.3 | Bangun consistent SQLite/assets backup, isolated restore dan maintenance CLI lokal | Fresh/upgrade/restart, disk/storage failure, WAL consistency, asset hashes, grants/revisions/jobs/checkpoints dan retention setelah restore |

Report JSON/CSV/HTML rendering/redaction/escaping milik B. A menyediakan lifecycle artifact, bukan merender report pengganti. Local recovery dilakukan non-container; off-host VM backup/operator dan deployment tetap tahap delivery.

## A10 — Acceptance mandiri dan handoff

**Prasyarat:** seluruh unit A01–A09 selesai dengan evidence, termasuk compatibility/historical migration yang diwajibkan.

| Unit sesi | Pekerjaan terbatas | Bukti selesai |
| --- | --- | --- |
| A10.1 | Jalankan acceptance Paket A, shared contracts track A, schema drift dan security/recovery/performance checks | API/SQLite nyata + fake B; S01–S12 sesuai scope; measured platform timing/capacity, termasuk 60 menit replay, metadata 100 sesi, 20 objek dan dukungan aset dua kanal sampai 2 jam; catat environment/limits |
| A10.2 | Susun manifest dan handoff ke integrasi Phase 10 | Candidate SHA/input versions; entrypoints/routes/migrations/config/dependencies, handlers/snapshot/purge registrations, inventory, commands/results, remaining limitations |

Paket A selesai tidak membuat parent Phase 6/9 otomatis selesai karena masih ada bagian B. G-BE tetap menunggu implementasi B, real provider smoke, composition/integration dan acceptance gabungan Phase 10. Jangan menaikkan production readiness berdasarkan fake analysis.

## Aturan setiap sesi untuk mengurangi halusinasi

1. Baca rules, handoff, unit aktif dalam dokumen ini, bagian PRD terkait, frozen contracts dan source/tests yang benar-benar dipakai. Jangan memuat seluruh roadmap sebagai task implementasi sekaligus.
2. Catat input SHA/working-tree state, entry dependency yang sudah terbukti, acceptance dan file/modul yang akan disentuh. Jangan menganggap dokumentasi atau folder kosong sebagai perilaku tersedia.
3. Kerjakan hanya unit aktif beserta prasyarat lokal yang diperlukan. Jika unit masih terlalu besar, pecah menjadi subunit sebelum coding; jangan diam-diam mengambil unit berikutnya.
4. Gunakan real A implementation dan fake B hanya melalui frozen ports. Laporkan gap kontrak beserta reproduksi; perubahan shared contract mengikuti version policy dan both-track checks. Jangan mengarang method/DTO untuk menghindari gap.
5. Jalankan meaningful tests sesuai risiko pada DB disposable, Ruff/mypy serta schema drift bila terdampak. Full checks pada akhir tahap atau ketika perubahan lintas modul memerlukannya; hasil sebelumnya dicatat, bukan diklaim sebagai run baru.
6. Perbarui status unit/tahap, `.agent/sessionHandoff.md` dan roadmap ketika implementasi substantif selesai. Pisahkan source tersedia, tests/build lulus, runtime berjalan, provider verified dan domain validation.
7. Catat blocker dan next action yang konkret. Unit belum `done` bila acceptance wajib belum terbukti. Hentikan runtime milik sesi saat tidak diperlukan.

Format handoff minimum:

```text
Unit aktif dan status:
Input SHA / perubahan lokal:
Deliverables / files:
Acceptance: terbukti / belum terbukti:
Checks: command, environment, hasil:
Contract/migration/config versions:
Blocker / limits:
Runtime / cleanup:
Next unit dan entry dependencies:
```

Prompt untuk satu sesi:

```text
Saya Pihak A. Kerjakan unit A01.1 sesuai
docs/development/package-a-execution.md.
Baca .agent/rules.md dan handoff terlebih dahulu; periksa entry dependencies
pada source dan evidence. Implementasikan hanya unit tersebut,
jalankan checks yang relevan, lalu perbarui progress dan handoff.
Jangan lanjut ke unit berikutnya atau integrasi B.
```

Ganti `A01.1` dengan unit berikutnya setelah acceptance unit sebelumnya terbukti. Plan ini tidak memberi izin commit/push/deploy otomatis.

## Referensi

- [Roadmap dan gate](../../.agent/implementationPhases.md).
- [Packet A/B](backend-packets.md).
- [Ownership/transaksi](../architecture/backend-baseline.md).
- [Shared contracts/version policy](../api/shared-contracts.md).
- [Foundation workflow](backend-foundation.md).
- [Evidence baseline](../testing/phase01-evidence.md).
