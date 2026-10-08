# Backend foundation workflow

Python target: 3.12.x (`>=3.12,<3.13`), dibuktikan pada Python 3.12.14 macOS arm64. Toolchain awal uv 0.12.23; `uv.lock` mengunci resolved direct/transitive packages dan hashes. `pyproject.toml` root membangun package dari `backend/flowlens` dengan Hatchling. Tidak ada package manager sebelumnya yang diganti.

## Setup

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install uv==0.12.23
.venv/bin/uv sync --locked
```

Gunakan Python 3.12 yang tersedia pada mesin; jangan memakai system Python 3.9. `.venv` lokal di-ignore. Runtime dependencies kini FastAPI/Pydantic/Uvicorn dan argon2-cffi (A02.1). Google SDK, Shapely dan FFmpeg akan ditambahkan oleh owner A/B pada fase implementasinya, dengan lock dan compatibility checks; foundation tidak mengklaim adapter tersebut tersedia.

## Checks

```sh
.venv/bin/ruff check backend tests scripts
.venv/bin/ruff format --check backend tests scripts
.venv/bin/mypy
.venv/bin/pytest tests/contracts
.venv/bin/python -m flowlens.contracts.generate --check
.venv/bin/bandit -r backend/flowlens -ll
.venv/bin/pip-audit --local
git diff --check
```

`pip-audit` memakai advisory network; laporkan outage/unavailable terpisah. Bandit adalah static scan, bukan audit keamanan lengkap. Tidak ada frontend/browser/Compose checks pada foundation.

## Standalone A/B

```sh
.venv/bin/pytest tests/contracts --track A
.venv/bin/pytest tests/contracts --track B
.venv/bin/python -m flowlens.testing --track A
.venv/bin/python -m flowlens.testing --track B
```

Pytest kedua track menjalankan suite kontrak yang sama dengan registration bundle sesuai track. CLI membuat tempdir/SQLite disposable, memuat fixture input dan hanya menjalankan contract smoke MOCK; tidak melakukan provider calls. Semua temporary connections ditutup, tempdir dihapus, tidak ada daemon.

Optional local contract app memakai factory `flowlens.api.app:create_app`, default MOCK. Routes `/_harness/*` hanya validasi kontrak; tidak mengimplementasikan import/replay/STT/findings bisnis. `/ready` false/BASELINE_ONLY, production settings ditolak. Untuk inspeksi lokal, gunakan `.venv/bin/uvicorn flowlens.api.app:create_app --factory --host 127.0.0.1 --workers 1`; pengguna menghentikan dengan Ctrl-C. Tidak ada server yang perlu berjalan untuk tests.

## Host Paket A — A01.1

Host A terpisah dari baseline contract harness:

```sh
.venv/bin/python -m flowlens.api.serve
```

Default bind `127.0.0.1:8000`, satu process, tanpa reload. Hentikan dengan Ctrl-C. Environment yang didukung: `FLOWLENS_PROFILE` (`development`/`test`), `FLOWLENS_HOST` (loopback IP), `FLOWLENS_PORT` (1–65535), `FLOWLENS_API_WORKERS` (hanya `1`). `WEB_CONCURRENCY`/`UVICORN_WORKERS` selain `1`, unknown `FLOWLENS_*`, dan production ditolak. Tidak membaca `.env` atau mengeluarkan values invalid ke terminal.

Factory untuk test/composition adalah `flowlens.api.host:create_host`; modules disuntikkan melalui frozen ModuleRegistration. Fake B hanya di test profile. Host default tanpa database_path tidak mengimpor `flowlens.testing`, tidak membuka DB dan tidak memasang harness validators. `/health` alive, `/ready` 503/HOST_ONLY, `/release.json` safe identifiers. Pada A01.1 ownership baru dibatasi lewat config/launcher; A01.2 menambahkan POSIX owner lock untuk DB terkonfigurasi.

Checks unit: `.venv/bin/pytest tests/platform/test_host.py -q`. Detail hasil dan limits saat unit tersebut selesai: [evidence A01.1](../testing/a011-evidence.md). Business APIs/auth/provider belum tersedia; persistence foundation ditambahkan pada A01.2 di bawah. Production OpenAPI/client tetap menunggu Phase 10.

## Persistence Paket A — A01.2

Untuk host dengan SQLite privat:

```sh
FLOWLENS_DB_PATH=data/database/flowlens.sqlite3 .venv/bin/python -m flowlens.api.serve
```

Setting path bersifat optional: tanpa path, host tetap berjalan tanpa DB. Dengan path, lifespan mengambil POSIX owner lock, memvalidasi/applies immutable migration manifest, membuka WAL/FK/FULL-synchronous runtime dan melepas ownership saat shutdown. Tabel platform tersedia; tidak ada analysis tables atau auth/import/job lifecycle APIs. Existing DB harus mode privat (0600); unversioned archive ditolak sampai A01.3. Jangan memakai DB developer/shared sebagai fixture migration tests.

Service/repository memakai `Database.begin()` dan explicit `uow.commit()`; exception/missing commit rollback. Retained repository tidak dapat dipakai setelah UOW selesai. Repository extensions B memakai factory `analysis`/`analysis.*` dengan connection dan guard UOW yang sama; real composition tetap Phase 10. Callbacks dijalankan sesudah durable commit/connection close; publication failure perlu resync, bukan membalik data committed. Jangan menahan UOW selama provider call.

Checks: `.venv/bin/pytest tests/platform -q`. [Evidence A01.2](../testing/a012-evidence.md) mencatat fresh/upgrade/atomicity/ownership/concurrency/build dan limitations. `/ready` tetap 503/HOST_ONLY; produksi/backend lengkap belum tersedia. `*.owner.lock` dibiarkan pada private directory setelah shutdown, tanpa lock aktif; jangan unlink lock file saat runtime berjalan.

## Historical archive — A01.3

Migrasi unversioned archive tetap action eksplisit ke file berbeda: `.venv/bin/python -m flowlens.cli.migrate_archive --source /private/old.sqlite3 --target /private/new.sqlite3`. [Compatibility guide](legacy-compatibility.md) menetapkan audited profile, original-ID mapping, quarantine/private boundary dan auth deprecation; [evidence A01.3](../testing/a013-evidence.md) mencatat preservation/rollback/WAL/CLI tests. Host tidak otomatis meng-upgrade format lama atau menerima credential/operator token lama.

## Accounts — A02.1

Private one-time bootstrap: `.venv/bin/python -m flowlens.cli.bootstrap_admin --database data/database/flowlens.sqlite3 --login admin`, password via interactive getpass. Untuk secret deployment, optional owner-only `--password-file`; jangan memberi password lewat argv. [Account lifecycle guide](account-lifecycle.md) menetapkan Argon2 parameters, force-change dan credential-version checks. [Evidence](../testing/a021-evidence.md) mencatat disposable tests/dependency compatibility; tidak ada akun nyata dibuat oleh task ini. Record A02.1 mencakup service/CLI; HTTP lifecycle tersedia melalui A02.2 di bawah. Readiness tetap 503.

## HTTP auth — A02.2

Host dengan DB/individual bootstrap kini memasang login/session/password/logout routes. [Authentication guide](authentication.md) menetapkan Origin/CSRF, opaque HttpOnly cookies, Secure HTTPS, durable expiry/revoke, fixed-window limits, forwarding policy dan local DTOs. Origin default mengikuti host/port; optional FLOWLENS_ORIGIN adalah exact HTTP(S) origin. Supported launcher kini proxy_headers=false; VM trusted proxy topology tetap Phase15. [Evidence A02.2](../testing/a022-evidence.md) membuktikan service/HTTP/real process smoke; grants/context/WS/media policy berikutnya A03/A07. Readiness tetap503.

## Regenerate shared artifacts

```sh
.venv/bin/python scripts/fixtures/build_baseline.py
.venv/bin/python -m flowlens.contracts.generate
```

Fixture builder mempertahankan speech waveform yang ditrack dan menghitung ulang metadata/hash. Generator kontrak hanya mengubah schemas/OpenAPI. Review diff dan jalankan drift tests setelah regeneration. Jangan mengedit generated schemas dengan tangan.
