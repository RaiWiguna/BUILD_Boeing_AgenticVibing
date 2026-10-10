# Authorization foundation — A03.1

Host dengan DB menyediakan `app.state.permissions` dan memasang live guard pada UOW/repositories. Shared contract tetap 1.0.0. API transport dan public role/capability serializers tersedia melalui [A03.2](transport-policy.md); tidak ada endpoint domain/grant/worker baru pada unit ini.

## Human grants

Trusted server service `Permissions.grant`/`revoke` menerima credential sesi admin yang masih aktif, bukan actor ID yang diklaim klien. Target account harus aktif dan session harus ada. Grant berlaku untuk satu account/session/capability dengan expiry UTC epoch-ms dan revocation; perubahan dan audit berada dalam transaksi yang sama. Grant ulang mengganti expiry/role dan membuka revocation. [A03.3](mutation-consistency.md) menambahkan append-only enforcement dan general mutation infrastructure; trusted grant management belum mempunyai HTTP/version/idempotency endpoint.

| Role | Capability yang dapat diberikan secara eksplisit |
| --- | --- |
| observer | read, audio |
| controller | read, audio, review |
| evaluator | read, audio, review, analysis, export, truth |

Role tidak otomatis memberikan semua capabilities. Semua akses domain membutuhkan `read`; raw audio membutuhkan `audio`; export membutuhkan `export`; export audio juga membutuhkan `audio`. Truth membutuhkan explicit evaluator grant dan context DEBRIEF. Admin global hanya mengelola akses dan worker provisioning; admin tidak otomatis mempunyai read/audio/export/truth. Account/role bukan seat/position atau kewenangan clearance. Legacy grants tanpa expiry tidak aktif sampai diberikan kembali secara eksplisit.

## Server context dan transaksi

`human_context(token, session_id, run_id=..., required=...)` hanya dipanggil oleh handler server. Session/run merupakan selector yang diperiksa, bukan klaim authority. Actor berasal dari authenticated session; capabilities dari live grants; revision/hash dari platform revisions/runs; as-of/mode dari `platform_context_state`. `required` dipilih kode handler. Missing server replay state menghasilkan NOT_EVALUABLE; tidak ada fallback ke clock/body klien.

Importer/replay owner mengisi state saat A04/A07. Fondasi ini menggunakan latest input revision dan menolak run yang stale; historical run readers/disposition belum tersedia dan harus ditentukan pada A07. Mode/as-of dipin pada issued context, bukan cursor klien. Filtering event availability dan replay reducers dilaksanakan A07; A03.2 menyediakan observed projection guard dan menolak truth dari public serializer; memasukkan as-of pada context belum membuktikan filtering domain.

Context memiliki request UUID acak dan receipt durable berupa hash seluruh DTO, credential digest/principal/scope dan TTL lima menit. JSON example/body/browser/model tidak dapat menggantikan issued context. Handler wajib membangun context baru dari credential setiap request; receipt bukan endpoint penerimaan context klien. List capability yang diubah pada frozen DTO juga mengubah digest dan ditolak.

Setiap repository append/get (termasuk repository injection `analysis.*`), event enqueue, dan audit pada host memeriksa proof, session/logout/expiry/credential-version, grant expiry/revocation, scope dan revision dalam UOW yang sama dengan akses data. Context lama setelah logout/reset/revoke ditolak; expired context harus dibangun ulang. Pemeriksaan service tambahan memakai `permissions.enforce(uow, context)` sebelum operasi domain. Raw SQL tetap trusted API infrastructure; direct standalone Database tanpa guard hanya untuk migration/bootstrap/storage tests, bukan boundary request. Worker tidak membuka database.

## Worker boundary

`provision_worker` hanya trusted provisioning melalui sesi admin, tanpa browser route. Credential opaque berprefix `wrk_`, SecretStr saat sekali dikembalikan, hanya SHA-256 digest disimpan. Human credential dan worker credential tidak dapat dipertukarkan. Rotation dilakukan dengan revoke credential lama dan provision credential baru; tidak ada default/secret publik.

`bind_worker` mengikat principal ke satu session/run/revision, server as-of, expiry dan explicit source/asset IDs. Admin yang mengikat juga harus mempunyai read/analysis grant untuk session tersebut. Allowlist bounded; cross-session/missing assets/sources ditolak dan seluruh binding rollback. Context worker selalu AS_KNOWN dengan read/analysis/worker saja; tidak ada global audio/export/truth/review/admin atau inventory method. `revoke_scope` dan `revoke_worker` membatalkan context yang sudah diterbitkan. Restart mempertahankan receipts/revocation.

Ini fondasi scope, belum job lease/heartbeat/attempt/result commit. A06 harus menghubungkan scope dengan valid lease, deadline/cancel/revision dan recheck source rights sebelum transfer serta accepted commit. Bearer transport/internal browser denial tersedia pada [A03.2](transport-policy.md); proxy network isolation tetap Phase15; tidak ada endpoint internal yang dibuka sekarang.

## Source dan asset rights

`require_source_rights` memeriksa issued context, exact source/session/revision, strict manifest dan source hash, serta local permission. Cloud juga membutuhkan analysis dan cloud permission. Export audio membutuhkan kedua export/audio_export source permissions. Worker hanya dapat memeriksa source dalam allowlist. Missing/malformed/mismatched manifests fail closed.

`authorize_asset` memeriksa explicit human audio grant atau worker asset allowlist, exact revision/source/asset/hash dan local source rights. Return hanya Asset metadata dengan fixture_path dihapus; private storage_key tidak dikembalikan. Route media/range sebenarnya tetap A05, export/download tetap A09. Semua handler sumber harus memakai pemeriksaan ini; pemeriksaan context saja belum menggantikan rights per sumber atau filtering domain.

[Evidence dan cakupan test](../testing/a031-evidence.md). Readiness tetap HOST_ONLY/503; seluruh gates belum berjalan.
