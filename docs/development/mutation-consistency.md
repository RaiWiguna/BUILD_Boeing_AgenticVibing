# Mutation consistency — A03.3

Tanggal: 9 Oktober 2026. Human aggregate mutation infrastructure tersedia di host melalui app.state.mutations. Contract/ports tetap 1.0.0; platform.0007 menambahkan versions, durable receipts dan append-only protections. Tidak menambah domain endpoint atau integrasi B.

## Registration dan authority

Composition A memasok tuple MutationOperation melalui create_host(mutation_operations=...). Default registry kosong. Registration menetapkan operation name, aggregate namespace, repository namespace, required review/analysis capability, exact payload Contract type, handler dan operation version. Registry immutable; body/header tidak menentukan handler, namespace atau permission. Naikkan operation version bila semantics berubah.

execute(context, operation, target_id=..., key=..., expected_version=..., payload=..., publish=...) memakai fresh server-built context A03.2. Semua akses membutuhkan live host context_guard. Worker ditolak: credential/scope A03.1 bukan lease dan tidak boleh menjalankan general aggregate mutation. Accepted worker/job result coordinator tetap A06 dengan attempt receipts terpisah.

Handler menerima context, validated payload dan frozen UnitOfWork port. Gunakan registered repositories/ports untuk domain write; tidak mengimpor internals B. Callback wajib memvalidasi target existence, ownership, domain transition dan source rights yang relevan. Grant session/run tidak membuktikan seluruh semantic precondition. Tidak ada provider/file/network work dalam writer transaction.

## Version dan idempotency

Aggregate version dimiliki tuple session/run/namespace/target. Missing bookkeeping adalah version0; accepted first creation menjadi1, selanjutnya increment dengan compare-and-swap. Ini tidak membuktikan target domain ada atau membuat session/run otomatis. Actual domain owner harus menyiapkan bookkeeping bersama initial aggregate creation; frozen Review.expected_version mulai1 tetap memerlukan initial target version1. Domain endpoint belum tersedia pada unit ini.

Opaque client key 1–128 ASCII characters A–Z/a–z/digits/underscore/dot/colon/hyphen. Gunakan satu key tetap untuk retry satu intent; request baru memakai key baru. Receipt identity adalah session/run/actor/operation/target/key digest. Expected version harus integer non-boolean, nonnegative dan berada dalam range SQLite increment yang didukung.

Normalized request hash mencakup validated JSON payload dengan sorted object keys, target, expected version, input revision/hash, registration/payload type/version dan repository namespace. List ordering tetap berarti. Request UUID, credential, mode/as-of dan transport headers tidak masuk hash; nonce/clock baru saat retry tidak menciptakan efek baru. Stored receipts/audit tidak menyimpan raw key/body/transcript/password; domain record/evidence tetap berada pada private repository yang sesuai.

Authorization diperiksa sebelum receipt lookup. Same key/request mendapat receipt asli, termasuk version/sequence saat commit tersebut, meskipun aggregate kemudian berubah. Changed payload/version/input atau registration semantics menghasilkan IDEMPOTENCY_CONFLICT409. New key dengan stale expected version menghasilkan VERSION_CONFLICT409. Revoke/logout/expired/forged context ditolak sebelum receipt bisa dibaca. Receipt hanya IDs/scope/version/sequence; bukan private result dump atau snapshot terkini.

## Satu commit

Coordinator melakukan hal berikut dalam satu real BEGIN IMMEDIATE/UOW:

1. Periksa authority, canonical payload, prior receipt dan expected version.
2. Jalankan domain callback; verifikasi accepted DTO scope/schema dan baca ulang hasil melalui registered Repository.get dalam UOW yang sama. Return tanpa persisted matching record tidak menghasilkan saved/success.
3. Increment aggregate version, enqueue event, append minimal audit dan insert receipt dengan FK ke aggregate/event/audit/revision/run.
4. Commit milik coordinator. Publication callback baru berjalan setelah durable commit dan connection close.

Fault domain/evidence/version/event/audit/receipt atau deferred-FK commit failure membatalkan semua writes dan publication. Domain callback tidak memiliki commit/rollback authority; UOW methods dan raw SQLite transaction/savepoint attempts ditolak. Attempt yang ditangkap callback membuat UOW rollback-only. Nested writer UOW tidak didukung.

After-commit publication failure tetap dilaporkan sebagai durable commit + resync required. Receipt/version/state tidak dibalik; retry key/payload yang sama mengembalikan receipt asli tanpa domain write atau callback publication kedua. Exactly-once local effect tidak menjamin event delivery/provider billing exactly-once. Publication/resync service nyata tetap A07.

## Audit dan immutable receipt

platform_audit, platform_account_audit dan platform_permission_audit serta platform_mutation_receipts memakai UPDATE/DELETE/replace protection. Insert guards juga memeriksa receipt composite identity sehingga INSERT OR REPLACE dengan UUID baru tetap ditolak, termasuk koneksi SQLite biasa tanpa recursive_triggers. Historical audit rows dipertahankan saat upgrade0006→0007.

Runtime UOW authorizer melarang edit/delete immutable rows, schema drop/rename protected tables/triggers, writable PRAGMA yang melemahkan safeguards, attach/detach dan transaksi dari caller. Connection memakai recursive_triggers=ON. Migrator tetap memakai trusted connection dan immutable migration manifest sendiri; schema fault-injection tests memakai disposable database saja.

Ini append-only enforcement pada schema/application SQL, bukan cryptographic tamper evidence atau pengamanan terhadap operator yang dapat mengganti DB file/menonaktifkan authorizer. Audit query/privacy/retention/maintenance policy tetap A09. Actor/target/request IDs, bounded action dan UTC waktu disimpan sebagai metadata minimal; existing account/grant service audit tetap atomik, belum otomatis mempunyai mutation HTTP/idempotency/version endpoints.

## Checks dan next

[Evidence A03.3](../testing/a033-evidence.md) mencatat fresh/upgrade/restart/concurrency/rollback/HTTP tests. Registered review callback diuji lewat fake repository menggunakan frozen ports; tidak ada real analysis implementation. Next A04.1 private upload staging/validation/preview. G-BE/readiness tetap belum lengkap.
