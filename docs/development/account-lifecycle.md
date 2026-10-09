# Accounts dan private bootstrap — A02.1

Tanggal: 9 Oktober 2026. Service akun/CLI dan [HTTP auth A02.2](authentication.md) tersedia; domain grants/context/worker policy berikutnya A03. Actor UUID pada management service adalah trusted internal input, bukan nilai yang boleh dipercaya dari browser. Service memeriksa active admin dan credential version saat melakukan mutation; HTTP actor resolution berikutnya menggunakan server session.

## Bootstrap

```sh
.venv/bin/python -m flowlens.cli.bootstrap_admin \
  --database data/database/flowlens.sqlite3 --login admin
```

CLI meminta password dua kali melalui `getpass` pada terminal interaktif. Tidak ada default password, auto-bootstrap saat API startup, password command-line argument, atau credential pada output. Bootstrap sekali sepanjang database lifetime menggunakan durable marker dan pemeriksaan admin; tidak dapat diulang hanya karena akun kemudian dinonaktifkan.

Untuk provisioning lokal dari secret deployment yang sudah ada, gunakan `--password-file /absolute/private/bootstrap.secret`. File harus regular, dimiliki effective OS user, tanpa permission group/other; symlink ditolak. Path harus di-ignore sebelum secret dibuat (misalnya private `data/`), dan isi tidak dimasukkan Git/log. Output sukses hanya account UUID, login dan status; failure disanitasi. Task ini tidak membuat akun/password nyata pada DB pengguna.

## Password dan account policy

- Login canonical casefold dengan pola ASCII `[a-z][a-z0-9._-]{2,63}`; duplicate canonical login ditolak.
- Password minimum 12 characters dan maksimum 4096 UTF-8 bytes. Tidak melakukan whitespace trimming atau mengubah password secara diam-diam; secret file boleh mempunyai satu trailing newline.
- Argon2id: time_cost=3, memory_cost=65536 KiB, parallelism=4, salt_len=16, hash_len=32. Library menghasilkan random salt; parameters eksplisit/versioned, bukan default platform yang tidak tercatat. [API resmi argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/api.html).
- Dependency direct `argon2-cffi>=25.1,<26`, resolved 25.1.0; bindings/cffi/pycparser hashes di uv.lock. Parameters ini sudah diuji lokal, belum merupakan capacity benchmark VM.
- Password API internal memakai SecretStr; account view tidak membawa hash/password. Stored hash tidak menjadi public DTO. Verifikasi dilakukan di luar write transaction; unknown account memakai dummy Argon2 hash dan error AUTH_REQUIRED yang sama. HTTP rate limits dan login timing acceptance tetap A02.2.
- Bootstrap admin tidak mendapat replay/domain/truth grant otomatis. Account berbeda dari Tower/Ground seat.

## Service dan revocation boundary

`flowlens.auth.accounts.Accounts` tersedia sebagai `app.state.accounts` selama configured DB lifespan. Repository/commands bersifat internal; admin users endpoint belum tersedia; HTTP login/session/password/logout tersedia melalui auth transport A02.2.

| Operasi | Aturan / hasil |
| --- | --- |
| bootstrap | Sekali, credential eksplisit; active admin tanpa forced change karena password dipilih melalui private provisioning |
| create | Active admin yang tidak sedang wajib ganti password; akun baru memakai temporary credential dan must_change_password=true |
| reset_password | Active admin; temporary credential supplied secara privat; version bertambah, must_change_password=true; tidak reactivates disabled account |
| change_password | Current password harus cocok dan account aktif; new password harus berbeda/valid; version bertambah, forced-change flag dilepas |
| deactivate | Active admin; last active admin tidak boleh dinonaktifkan; version bertambah dan access ditolak |
| verify_credentials | Password match + active + unchanged version; temporary credential hanya boleh masuk restricted password-change flow berikutnya |
| require_access | Recheck active/current version; stale credential AUTH_REQUIRED, forced change ACCESS_DENIED |

Session invalidation fondasi memakai monotonic credential_version. A02.2 wajib menyimpan version pada opaque server session dan recheck setiap request; A03/A07 mengikat WS/media/grants. Unit A02.1 membuktikan revocation snapshots; A02.2 menambahkan actual cookie/session checks. WS termination tetap A03/A07.

Password hashing berlangsung di luar UOW, kemudian actor/target/version diperiksa kembali sebelum commit. Audit account-scoped memakai IDs/actions/UTC saja dan berada pada transaksi yang sama. Password/hash/temporary credential tidak dicatat. Mutation yang gagal audit tidak mengembalikan saved state; accounts dan bootstrap marker rollback.

## Migration dan limits

`platform.0004` menambah is_admin/must_change_password/credential_version, durable bootstrap marker, dan account audit. Existing account rows dipertahankan tanpa promosi admin otomatis; unknown prior hashes tetap fail-closed. .0001–.0003 tidak diedit. SQLite ALTER CHECK membutuhkan read-only `quick_check`; authorizer mengizinkannya, tetap menolak transaction control, writable PRAGMA/foreign_keys changes, ATTACH dan migration-ledger changes.

Tidak ada public auth fallback/keyfile conversion/self-service recovery/email/production readiness dari A02.1. A02.2 menyediakan cookie/session/rate limits dan Origin/CSRF pada auth mutations; grants/generic CSRF tetap A03. Admin password reset merupakan trusted service; safe credential delivery dan restricted-change endpoint mengikuti auth transport berikutnya. Rehash-on-login serta session expiry/revoke sudah ditambahkan A02.2.

Evidence: [checks A02.1](../testing/a021-evidence.md). Next: A03.1 setelah A02.2 done.
