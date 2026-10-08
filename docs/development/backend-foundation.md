# Backend foundation workflow

Python target: 3.12.x (`>=3.12,<3.13`), dibuktikan pada Python 3.12.14 macOS arm64. Toolchain awal uv 0.12.23; `uv.lock` mengunci resolved direct/transitive packages dan hashes. `pyproject.toml` root membangun package dari `backend/flowlens` dengan Hatchling. Tidak ada package manager sebelumnya yang diganti.

## Setup

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install uv==0.12.23
.venv/bin/uv sync --locked
```

Gunakan Python 3.12 yang tersedia pada mesin; jangan memakai system Python 3.9. `.venv` lokal di-ignore. Runtime dependencies foundation hanya FastAPI/Pydantic/Uvicorn. Google SDK, Shapely, Argon2 dan FFmpeg akan ditambahkan oleh owner A/B pada fase implementasinya, dengan lock dan compatibility checks; foundation tidak mengklaim adapter tersebut tersedia.

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

## Regenerate

```sh
.venv/bin/python scripts/fixtures/build_baseline.py
.venv/bin/python -m flowlens.contracts.generate
```

Fixture builder mempertahankan speech waveform yang ditrack dan menghitung ulang metadata/hash. Generator kontrak hanya mengubah schemas/OpenAPI. Review diff dan jalankan drift tests setelah regeneration. Jangan mengedit generated schemas dengan tangan.
