# Runbook — Demo VM `flowlens.site`

| Atribut | Nilai |
| --- | --- |
| Status | Berjalan sejak 13 Oktober 2026; track demo (ADR 0003), bukan release G-DELIVERY |
| Host | Satu VM GCP Ubuntu 22.04 (2 vCPU, 3,8 GiB), user `deploy`; IP/key tidak dicatat di repo |
| Domain | `flowlens.site` (A record ke VM); `www.` redirect 301 ke apex |
| Source | Clone branch `feat/fe-init` di `~/flowlens` |

## Topologi

`edge` (Caddy 2.10.2: build Vite statis, TLS Let's Encrypt otomatis, proxy `/api/demo/*`) → `api` (demo FastAPI, satu worker) → `db` (PostgreSQL 16.9). Hanya port 80/443 (TCP + UDP/443) yang dipublikasikan; `api` dan `db` hanya di network Compose. File: [compose.yml](../../deploy/compose/vm/compose.yml), [Caddyfile](../../deploy/caddy/Caddyfile), [Dockerfile.edge](../../deploy/docker/frontend/Dockerfile.edge).

## Rute publik

| Path | Isi |
| --- | --- |
| `/` | Landing page pengenalan produk (mobile-first); tidak ada tautan ke sign-in |
| `/login-flow` | Sign-in dengan akun demo (kartu demo di halaman); `/login` redirect ke sini dengan query tetap |
| `/sessions`, `/s/...` | Aplikasi; tanpa sesi diarahkan ke `/login-flow?next=...` |
| `/api/demo/*` | Demo API (body request dibatasi 200 MB di edge) |

## Operasi

```bash
cd ~/flowlens
C="docker compose -f deploy/compose/vm/compose.yml --env-file deploy/compose/vm/.env"
git pull --ff-only && $C up -d --build   # update
$C ps; $C logs --tail 100 edge            # status / log
$C down                                   # stop (jangan pakai -v: menghapus DB dan sertifikat)
```

- `deploy/compose/vm/.env` (mode 0600, di-ignore Git) berisi `DEMO_DB_PASSWORD` acak yang dibuat di VM; tidak pernah dicetak atau disalin.
- Paket skenario privat (`data/demo-scenarios/`, ±195 MB) disalin dari workstation dengan `rsync` lewat SSH; checksum diverifikasi (0 selisih). Clone baru tanpa folder ini tetap menyajikan landing dan sesi seed, tetapi demo import tidak mempunyai skenario.
- Volume persisten: `pgdata` (workspace demo), `caddy-data` (akun ACME/sertifikat).

## Verifikasi 13 Oktober 2026

Lokal: lint, check:types, check:copy, 65 Vitest (4 baru untuk landing/rute), build PASS; screenshot mobile 390 px dan desktop 1440 px tanpa overflow horizontal atau console error. VM: `compose config`, `caddy validate`, build image, health `api`/`db` PASS; sertifikat untuk apex dan `www` diterbitkan. Eksternal: `/`, `/login-flow`, SPA deep link 200; HTTP→HTTPS 308; `www`→apex 301; `/api/demo/health` = database true, 6 skenario; HSTS/nosniff/DENY aktif; aset `immutable`, shell `no-cache`; port 8000/5432 tidak terjangkau. Playwright ke produksi: landing tanpa link login, guard `/sessions`→`/login-flow?next`, login Evaluator → `/sessions` tanpa error.

## Batasan yang diketahui

- Demo API **tanpa autentikasi server**: siapa pun dapat membuat workspace/upload melalui `/api/demo` (dibatasi ukuran). Login hanya MOCK di browser. Jangan menaruh data non-publik.
- Tidak ada backup DB, monitoring, image digest pinning, atau rollback otomatis; restart policy `unless-stopped` bukan high availability.
- Label status (MOCK, synthetic ADS-B, NOT_DOMAIN_VALIDATED) tetap berlaku sesuai ADR 0003.
