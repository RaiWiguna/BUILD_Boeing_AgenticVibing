# HTTP authentication — A02.2

Tanggal: 9 Oktober 2026. Individual login/session/password-change/logout tersedia pada host A dengan configured DB dan bootstrap akun. Grants/worker principals dan generic HTTP/WS policy tersedia melalui [A03.1–A03.2](transport-policy.md); actual domain/media/stream tetap unit owner. `/ready` tetap 503 karena pipeline backend belum lengkap.

## Local workflow dan origin

Bootstrap menggunakan [private CLI](account-lifecycle.md). Jalankan `.venv/bin/python -m flowlens.api.serve` dengan `FLOWLENS_DB_PATH` menunjuk private database; optional `FLOWLENS_PORT` mengubah bind port. Origin default mengikuti loopback host/port. `FLOWLENS_ORIGIN` dapat menetapkan exact HTTP(S) origin: HTTP hanya localhost/loopback; URL userinfo/path/query/fragment ditolak. HTTPS origin menghasilkan Secure cookie; test HTTPS membuktikan atribut cookie, bukan TLS deployment.

Supported launcher tidak mempercayai forwarding headers (`proxy_headers=False`). Peer rate key memakai actual ASGI client pada runtime tersebut; spoofed X-Forwarded-For/Proto tidak memberi trust atau mengubah cookie mode. Trusted edge proxy configuration untuk VM tetap Phase 15, bukan diasumsikan aktif sekarang.

Mutasi auth memerlukan `Origin` yang sama dengan configured origin. Cross-site Sec-Fetch-Site juga ditolak. Logout/password-change memerlukan `X-CSRF-Token` dari authenticated session response. Tidak ada CORS wildcard atau auth fallback bearer/query token.

## Endpoint contract

| Endpoint | Input / response |
| --- | --- |
| POST `/api/v1/auth/login` | Strict login/password body; Origin required. 200 safe AccountView + csrf_token + expires_ms; opaque credential hanya melalui Set-Cookie |
| GET `/api/v1/auth/session` | Cookie-only; 200 AccountView/CSRF/expiry. Temporary account mendapat must_change_password flag untuk restricted change flow |
| POST `/api/v1/auth/password` | Origin, cookie, CSRF, current_password/new_password; 204 dan clear cookie. Login ulang setelah sukses; semua prior account sessions invalid via new credential version |
| POST `/api/v1/auth/logout` | Origin dan CSRF jika cookie hadir; current token revoked, 204/clear cookie. Cookie absent dapat logout idempotent |

AccountView memuat UUID/login/active/is_admin/must_change_password/credential_version, tanpa password/hash. `expires_ms` adalah **UTC Unix epoch milliseconds untuk absolute auth expiry**, bukan relative replay time. Auth responses termasuk error memakai Cache-Control no-store. Additional actor/session/role fields pada input ditolak; server tidak memakai browser-supplied account identity.

Invalid credential/unknown/expired/revoked stamp → 401 AUTH_REQUIRED; Origin/CSRF/forced-change denial → 403 ACCESS_DENIED; malformed input → 422 INVALID_INPUT; throttle → 429 RATE_LIMITED dengan Retry-After integer. RATE_LIMITED adalah additive host transport code, bukan perubahan frozen domain ErrorCode 1.0.0. Auth local DTOs muncul pada host OpenAPI; baseline harness OpenAPI/JSON Schema tetap terpisah, final generated client freeze Phase 10.

## Durable sessions dan revocation

- 32 random bytes di-encode opaque cookie `flowlens_session`; SQLite menyimpan SHA-256 token digest, bukan raw token. Cookie HttpOnly, SameSite=Lax, Path=/, Max-Age 8 jam, Secure untuk configured HTTPS; tidak ada Domain attribute.
- CSRF token adalah HMAC-SHA256 dari fixed purpose menggunakan raw opaque token sebagai key. Bisa dihitung ulang setelah restart; digest di DB tidak cukup untuk mendapatkan raw session/CSRF credential. CSRF value masuk safe session JSON, cookie tetap HttpOnly.
- Idle expiry 60 menit; absolute expiry 8 jam. Valid resolve memperbarui last_seen saja; absolute deadline tidak diperpanjang. Exact deadline sudah expired. Clock mundur dari last_seen ditolak, bukan memperpanjang akses diam-diam.
- Session row menyimpan credential_version saat login. Setiap resolve membandingkan account aktif dan current stamp; reset/deactivation/password-change segera membuat stamp lama invalid pada request berikutnya.
- Default resolve menolak account yang wajib ganti password. Hanya session status, password-change dan logout flow memberi restricted access; role/admin flag tidak menghasilkan grants.
- Login merotasi cookie dan revokes supplied prior token. Logout revokes persistent row. Successful credential verification rehashes stored older Argon2 parameters jika perlu, dengan race check dan tanpa menaikkan credential_version untuk perubahan hash representation saja.
- Session creation/login audit satu transaksi; fault tidak mengirim Set-Cookie sukses. Credential parsing bounded; cookie/session tokens tidak diterima melalui URL/bearer headers atau audit/logs.

## Rate limit dan hashing bound

Durable fixed-window baseline: 5 credential attempts/account/60 detik, 20 login attempts/peer/60 detik; successful login juga dihitung. Password-change berbagi account budget. Counters reserved sebelum hashing, tersimpan melalui restart, expired windows dipruning; subject keys hashed dan maksimum 10.000 live rows, overflow fail-closed.

Hashing untuk HTTP login/password-change dibatasi dua calls bersamaan per service, di luar write transaction. Slot penuh membalas 429, bukan menjalankan unlimited Argon2 work. Admin/offline service users belum berbagi HTTP semaphore; future HTTP account-management harus menggunakan crypto budget yang sesuai. Limits ini engineering baseline, bukan load benchmark VM/SLA atau perlindungan DDoS menyeluruh.

## Limits dan next action

A02.2 sendiri hanya menyediakan auth routes; [A03.1](authorization.md) menambahkan grants/contexts/worker dan [A03.2](transport-policy.md) generic HTTP/WS policy serta public projection. Bearer/query/context claims kini ditolak 403 sebelum routing/body validation; transport Origin denial juga mendahului 422 malformed body. Actual domain/media/export routes dan real WS replay tetap unit owner. Admin user management endpoints belum tersedia; account service tetap internal.

Production profile tetap diblok sebelum G-BE. Tidak membuat akun/password nyata, provider calls atau deployment dalam unit ini. [Evidence A02.2](../testing/a022-evidence.md). General mutation infrastructure tersedia pada [A03.3](mutation-consistency.md); next A04.1.
