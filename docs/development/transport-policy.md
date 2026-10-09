# HTTP/WS transport dan public projection — A03.2

Tanggal: 9 Oktober 2026. Host memasang generic transport guard dan menyediakan scoped helpers serta public serializer. Contract 1.0.0, migrations platform.0001–.0006 dan dependency lock tetap. Tidak menambah route domain, jobs, media/export atau replay stream nyata.

## Boundary host

| Boundary | Credential dan policy |
| --- | --- |
| `/api/v1/*` selain empat auth routes | Opaque human cookie aktif; forced password change tidak dapat mengakses domain. GET/HEAD/OPTIONS boleh tanpa Origin; Origin jika hadir wajib exact match, cross-site Fetch Metadata ditolak. Mutation wajib exact Origin dan X-CSRF-Token |
| Auth login/session/password/logout | Pemeriksaan headers yang sama; endpoint mempertahankan login tanpa cookie, restricted password-change dan logout tanpa cookie. Origin/header policy diperiksa sebelum validasi body; CSRF logout/password tetap diperiksa oleh endpoint auth |
| `/internal/*`, `/api/v1/internal/*` | Opaque `Bearer wrk_...` aktif; human token, Cookie, Origin, Referer, CSRF dan Fetch Metadata ditolak. Principal-only check tidak memberi izin job/source/asset |
| WebSocket host | Human cookie aktif + exact Origin sebelum accept; internal WS ditolak. Scope/capability membutuhkan `websocket_context` sebelum accept dan pada publication berikutnya |

Duplicate security headers, duplicate session cookies, query credential/context/role/capability claims dan context/worker-token headers ditolak. Tidak ada fallback credential dari body/URL/subprotocol. Supplied forwarding headers tidak dipercaya oleh launcher. API/internal responses termasuk errors memakai no-store dan server request ID. Legacy bearer/operator routes tetap absent; request dengan legacy bearer sekarang ditolak 403 sebelum routing, bukan 404.

Guard HTTP berjalan di threadpool sebelum route dispatch. Liveness/readiness/release/docs serta test harness di luar API prefix tidak menjadi domain authorization boundary. Real module routes wajib memakai prefix API/internal yang sesuai. Browser-origin denial tidak membuktikan network isolation: proxy denial internal routes dan trusted TLS/proxy configuration tetap Phase 15.

## Scoped handler helpers

`http_context(request, session_id, run_id=..., required=...)` memeriksa transport dan membangun fresh human RequestContext melalui Permissions. Session/run merupakan selector yang diperiksa; actor, capabilities, revision/hash, mode dan as-of tetap dari server. Pilih required capability sebagai konstanta handler; jangan menerima required/role/context dari body atau query. Panggil helper dalam sync route, atau jalankan melalui threadpool dari async route.

`worker_context(request, scope_id)` hanya berlaku pada internal path, memakai bearer dan scope yang dibuktikan milik principal tersebut. Scope ID adalah selector, bukan authority. Principal-only authentication dipakai sebagai fondasi lease endpoint berikutnya; A06 tetap harus memeriksa actual lease, attempt, deadline/cancel, source rights dan accepted commit.

`await websocket_context(websocket, session_id, run_id=..., required=...)` dipanggil sebelum accept, dan kembali sebelum publikasi berikutnya. Policy memeriksa logout/reset/expiry/grant revocation dari durable state. TestClient probe membuktikan recheck; belum ada scheduler/subscription/push disconnect atau sequence/snapshot/resync untuk replay nyata. Semuanya tetap A07.3. Gunakan context baru hasil recheck untuk DTO berikutnya; jangan hanya menyimpan context handshake.

Principal guard host tidak menggantikan object/operation authorization. Setiap handler harus memilih capability yang tepat, membangun context dan memakai guarded UOW/repositories; media/export/source juga memeriksa rights spesifik. HTTP helpers dipanggil dari handler dengan konstanta server, bukan dipasang langsung sebagai Depends yang mengekspos parameter policy sebagai query.

## Public serializer

`public_dto(permissions, uow, context, value, classification="OBSERVED")` dijalankan dalam UOW akses data yang sama, setelah source/domain reader memilih proyeksi observed. Serializer membaca ulang live proof/grants/revision; worker ditolak. Caller adalah trusted handler, classification tidak berasal dari klien.

- Hanya exact frozen public DTO bertipe dan scoped yang diterima. Raw dict, internal RequestContext/JobResult/lease/artifact/tools, subclass dengan fields tambahan, serta TRUTH/PRIVATE classification ditolak. DTO copied/list-mutated divalidasi ulang; semua nested scopes/revisions diperiksa.
- Snapshot mode/as-of sesuai issued context. Timed rows yang future atau unknown/future availability pada AS_KNOWN ditolak; Brief/Option tidak boleh future as-of. Ini guard projection, bukan reducer/history filtering pengganti A07.
- Manifest memakai current persisted source rights/metadata. Tanpa explicit audio grant, assets kosong; dengan audio grant, setiap asset melewati authorize_asset dan fixture_path dihapus. Coverage audio tetap mencatat keberadaan sumber, bukan izin playback. Input tidak dimutasi.
- Tidak ada truth wire DTO frozen. Truth tetap tidak dapat dimasukkan melalui serializer publik meskipun evaluator memiliki truth grant. Route evaluator berikutnya memerlukan kontrak khusus yang direview; jangan membungkus truth sebagai SourceEvent observed. Admin/provider metadata memerlukan boundary admin tersendiri, bukan serializer replay ini.
- Typed DTO tidak dapat mendeteksi truth/secret yang sengaja dimasukkan dalam field teks yang sah. Trusted readers tetap harus memisahkan observed/truth, legacy seeds/schedules dan private records; legacy readers serta semantic evidence eligibility tetap A07/A05/B. Serializer tidak melakukan redaction berbasis tebak isi teks.

Handler dapat mengembalikan hasil dictionary dengan response_model canonical yang sesuai. Serializer tidak otomatis membungkus respons arbitrary; domain endpoints harus menggunakannya secara eksplisit. Frozen schema tidak berubah dan OpenAPI business/client final tetap Phase 10.

## Safe WS errors

Unauthorized/invalid path/body dan ContractError/HTTPException menutup dengan code 1008, reason kosong. Unexpected service error menutup 1011, reason kosong. Tidak mengirim validation input, exception, SQL, credential atau private path. Authenticated socket disconnect normal tidak dianggap service failure.

[Evidence A03.2](../testing/a032-evidence.md). [A03.3](mutation-consistency.md) kini menyediakan append-only audit, optimistic version dan durable mutation idempotency. Next A04.1.
