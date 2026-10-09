# ADR 0002 — Shared contracts and independent backend harnesses

Status: accepted for Phase 0–1 execution. Tanggal: 8 Oktober 2026.

Context: aplikasi direset; A/B harus bekerja independen setelah baseline, tanpa source dependency lintas paket dan tanpa integration slice sebelum Phase 10.

Decision: root pyproject/uv.lock, Python 3.12, canonical strict Pydantic contract version 1.0.0, SDK-independent Protocol ports dan version-checked ModuleRegistration. Domain/service code tidak mengimpor SDK/host storage internals. Harness MOCK memakai constrained disposable SQLite reference schemas; production settings menolak baseline/mock composition. Migration registration dependency ordering deterministic; cross-package constraints tidak dimatikan untuk tests. Public/internal schemas dihasilkan dari Pydantic; final OpenAPI/TS client menunggu actual composition.

Consequence: fixtures, reference schemas dan contract behavior dapat digunakan A/B sebelum real implementations. Contract/fake pass hanya foundation acceptance; provider smoke, geometry/domain correctness dan integration tetap wajib pada owner phases/10. Breaking contract perubahan memerlukan versioned reconciliation/adapter. SQLite harness bukan production job/persistence engine.

Validation: shared suite both tracks, strict/negative examples, scope/as-of/evidence checks, atomic rollback/receipt/publication, fresh/upgrade reference schema, module/migration registration, schema drift, lint/type/build/dependency scans. Real A/B migrations and provider SDK compatibility are verified later.

## Platform persistence elaboration — 9 Oktober 2026

Status: accepted implementation detail untuk ownership/transaction decision yang sama. Paket A menyediakan local POSIX advisory lock sepanjang DB lifespan; API serializes UOW, memakai WAL/FULL synchronous/FK dan explicit commit. Checksum migration mencakup ID/owner/dependency/SQL; applied manifest mismatch, downgrade dan unversioned archive ditolak. Pending migrations diterapkan dalam satu transaksi, bukan sqlite executescript yang dapat memutus batas transaksi.

Platform schema memakai scoped composite FKs dan unique receipts. Tabel minimal disempurnakan melalui migrations baru saat lifecycle domain dibangun. B meng-inject repository factories melalui same connection/UOW guard; tidak ada worker DB mount atau analysis tables dari Paket A. After-commit publication berlangsung setelah transaksi/connection dilepas; failure dilaporkan sebagai durable commit dengan kebutuhan resync, tidak rollback data.

Consequences: owner lock bekerja pada local canonical paths untuk process yang mematuhinya; Windows/network filesystem/hard-link aliases belum didukung/verified. Unversioned historical mapping tetap pekerjaan terpisah; optional host database path tidak otomatis membuktikan full readiness. [Validation dan limits A01.2](../testing/a012-evidence.md) mencatat fresh/upgrade, rollback, process lock, concurrent sequence dan real host restart; G-BE tetap belum passed.

## Historical archive preservation — 9 Oktober 2026

Audited pre-reset profile dikonversi dari read-only snapshot ke separate target lewat UOW. Original short IDs dan JSON text dipertahankan pada quarantine tables; canonical session UUID adalah deterministic UUIDv5 alias, bukan penggantian diam-diam pada source. Private checkpoints terpisah dari public archive rows, tanpa observer/provider adapters. Logical digest termasuk WAL-visible data menghasilkan idempotent receipt; changed same-ID archive ditolak. Unversioned in-place startup upgrade tetap ditolak.

Old operator keys/seat tokens bukan individual identities dan tidak di-grandfather menjadi accounts/grants. Public/training compatibility tetap perlu scoped readers/serializers pada replay phase; source label public historis tidak membuktikan seed/assessment safe bagi observer/AI. [Evidence A01.3](../testing/a013-evidence.md) dan [compatibility mapping](../development/legacy-compatibility.md) membuktikan preservation/atomicity/deprecation pada sintetik.

## Individual account lifecycle — 9 Oktober 2026

Platform.0004 menambahkan admin/forced-change/credential-version fields, durable one-time bootstrap marker dan account audit terpisah dari replay-session audit. Password memakai pinned argon2-cffi dengan explicit Argon2id parameters/random salts; password hashing dilakukan di luar write transactions, kemudian authority/credential version diperiksa kembali sebelum commit. Reset/change/deactivation menaikkan credential_version; transport session implementation harus memeriksa stamp tersebut setiap akses pada A02.2.

Bootstrap lewat local private getpass/secret file dan tidak memberikan replay/truth grants otomatis. Existing accounts tidak dipromosikan menjadi admin pada upgrade; public Account view tidak memuat hashes. HTTP/session/CSRF/grant boundaries masih fase berikutnya. [Account evidence](../testing/a021-evidence.md) membuktikan active-admin guards, race/rollback, forced change dan private CLI.

## Opaque HTTP sessions — 9 Oktober 2026

Platform.0005 menyimpan token digest, account credential stamp, UTC wall-clock timing dan revocation, bukan provider conversation state atau raw cookie. Supported local launcher tidak mempercayai forwarding headers; exact configured Origin menentukan auth policy/cookie Secure mode. Auth mutations memiliki Origin/CSRF guards sebagai prerequisite transport; generalized object/worker/WS/media policy tetap A03/A07.

Idle60min/absolute8h dengan durable stamp checks, forced-change restricted flow, cookie rotation/logout dan rehash-on-success disertai rate reservations sebelum hashing. Fixed-window account/peer limits serta two-slot hashing gate adalah initial engineering baseline, bukan VM capacity claim. [Auth evidence](../testing/a022-evidence.md) dan [contract](../development/authentication.md) mencatat SQL/HTTP/restart/throttle/CSRF tests dan live loopback smoke; production readiness tetap belum passed.
