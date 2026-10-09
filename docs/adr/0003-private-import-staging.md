# ADR 0003 — Private import drafts sebelum domain commit

Status: accepted; implemented untuk preview. Tanggal: 9 Oktober 2026.

Context: imported files untrusted, dapat besar dan malformed; multipart framework dapat membuat temporary files sebelum service memeriksa batas. File system dan SQLite tidak menyediakan transaksi atomik bersama. File name input bukan storage authority. Preview harus tersedia tanpa menerbitkan domain session atau mengirim data ke provider.

Decision: gunakan streaming multipart callbacks ke owner-only opaque fd storage dengan byte/hash limits selama write. Store draft metadata terpisah dalam platform schema; live account authority dan owner scope diperiksa sebelum finalization/read. Audio decoder menerima fd melalui fixed subprocess argv dengan CPU/wall controls, bukan input path/shell. Canonical versioned sidecar profiles diperiksa melalui frozen strict DTOs, tanpa normalization implicit. Preview selalu menunjukkan undeclared rights dan unknown alignment/layout; tidak menghasilkan worker input.

Rationale: batas upload berlaku sebelum full buffering; nama dan MIME tidak menjadi trust boundary; decode native tidak berjalan di host process. Domain state tetap absent ketika parsing/inspection gagal. Draft key receipt memberi stable retry tanpa menjanjikan import dedup atau FS promotion. Alternatives: framework UploadFile spooling tidak dipilih karena private staging/size policy baru berjalan setelah parsing; decoder in-process tidak dipilih karena native failure/resource lifecycle memengaruhi host langsung; ZIP extraction ditolak agar archive traversal tidak menjadi tambahan scope.

Impact: soundfile/python-multipart runtime dependencies dan lock; additive platform.0008; optional import root setting dan exclusive POSIX owner lock; new private POST/GET API local host schema. Shared contracts1.0.0 tetap. Admin-only draft creation digunakan karena global evaluator import grant belum didefinisikan; bukan automatic replay/truth/audio grant. Startup recovery membersihkan interrupted/expired/orphan draft bytes; accepted preview metadata/files dipertahankan.

Consequences/risks: subprocess bukan security sandbox dan tidak menjamin hard memory ceiling pada macOS. Supported Darwin runtime menolak memory rlimit; byte/metadata/frame/buffer, CPU dan wall controls digunakan dan limitation dicatat. Linux RLIMIT_AS behavior belum diuji. TTL cleanup hanya startup, quota finite; database/filesystem crash consistency tidak sama dengan atomic promotion. Native library dependency audit tidak tercakup penuh oleh Python pip-audit. File hashes menjamin integrity check terhadap recorded draft, bukan data rights atau forensic tamper-proof log.

Validation: [A04.1 evidence](../testing/a041-evidence.md) mencatat real WAV/FLAC decoder, malformed/nonfinite/traversal/hash/size/authority/HTTP/retry/restart/timeout checks dengan synthetic inputs/disposable storage; lint/type/contracts/build/dependency/security checks. Tidak ada live provider/domain validation atau capacity claim.

Follow-up: manifest/rights/coverage/timezone/identity/units/layout normalization pada A04.2; immutable committed source reader, promotion/dedup/conflict dan boundary crash tests pada A04.3; evaluator import authority jika capability tersebut dikontrak eksplisit; operational sandbox/retention/capacity sebelum release gate.

## Immutable preparation metadata — 9 Oktober 2026

Private draft menyimpan full provenance/granular tri-state rights/retention/coverage, per-file clock calibration, evidenced entity mappings dan declared local layout melalui immutable version/key receipts (platform.0009). Metadata revision/hash/actor/server time satu UOW; draft TTL cascade tetap membersihkan scratch, sehingga journal ini tidak diklaim committed-source audit. No FS promotion/domain writes.

Full envelope authoritative untuk future commit. Frozen1.0.0 SourceManifest hanya conservative projection: cloud memerlukan audio+context permission, local shared projection memerlukan reviewer permission, dan linear drift diproyeksikan unknown agar tidak hilang menjadi offset-only. Owner local preparation terpisah dari shared reviewer access. Histori receipt tidak memberi current transfer authority; fresh owner/token/file/latest-metadata preflight diperlukan.

Canonical sidecar validation berbagi records iterator dengan staging; normalization metadata retains raw values, scoped IDs dan uncertainty/nulls. Wall-time conversion eksplisit IANA/DST/UTC, layout m/ft conversion memakai versioned local profile; unsupported geographic/unknown-unit adapters ditolak. METADATA_COMPLETE adalah kelengkapan metadata, bukan domain/conformance verdict. [Validation A04.2](../testing/a042-evidence.md), [workflow](../development/import-metadata.md). Source commit/promotion dan cross-domain rights enforcement tetap pekerjaan berikutnya.
