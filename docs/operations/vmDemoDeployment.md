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
- Belum ada backup rutin/terenkripsi di luar VM, monitoring, image digest pinning otomatis, atau rollback otomatis; snapshot manual deployment bukan restore rehearsal atau high availability.
- Label status (MOCK, synthetic ADS-B, NOT_DOMAIN_VALIDATED) tetap berlaku sesuai ADR 0003.


## Perbaikan import dan deployment frontend — 13 Oktober 2026

Candidate source **8437e0a** (`feat/fe-init`) memperbaiki auto recognition case saat main kosong dan individual Choose yang sebelumnya melewati scoped placement. Screenshot error 50 berhasil direproduksi sebelum deployment, sementara API sudah memuat enam cases. Rincian perilaku: [panduan import](../development/demoWorkspace.md#perbaikan-pengenalan-import--13-oktober-2026).

Pre-deploy: 74 frontend tests, typecheck/lint/check:types/check:copy/build PASS; enam browser dry-runs frontend lokal dengan live catalogue VM, POST diintercept. Backend tidak berubah, sehingga 28 backend tests dari expansion tetap evidence historis, tidak dilaporkan dijalankan ulang pada fix ini.

Deployment hanya menjalankan `build edge` dan `up -d --no-deps --no-build edge` pada Compose VM setelah fast-forward branch ke candidate. Build normal Dockerfile.edge berhasil; dependency layers dari lockfile tersedia dalam cache build. Container API dan DB mempertahankan ID sebelum deployment; volume DB/sertifikat dan private assets tidak diganti. Image frontend yang berjalan: `sha256:44d5c79110df4569c4d622f6ccf69ed4c02c40e8f4fa154aeacd84e94eb852ce`. Bundle `ImportPage-2WHeTtUR.js` eksternal mempunyai SHA sama dengan build lokal.

Sebelum deployment, snapshot PostgreSQL custom-format dibuat melalui `pg_dump`, TOC diperiksa dengan `pg_restore -l`, dan image edge sebelumnya ditag `flowlens-edge:rollback-import-20261013`. Snapshot/image metadata dan 39 asset fingerprints disimpan privat dalam `~/flowlens-backups/import-fix-20261013-2u5mts/`. Snapshot tidak dicetak/dimasukkan Git; ini backup manual di VM yang sama, tanpa restore rehearsal. Seluruh 39 fingerprints tetap identik setelah deploy, termasuk assets 87/88. Caddy validate, API health (database true, 6 scenarios), `/`, `/login-flow`, `/sessions/import` HTTP 200 PASS.

Rollback frontend bila diperlukan: gunakan image bertag rollback dalam override Compose service `edge`, lalu `up -d --no-deps --no-build edge`. Jangan restore DB untuk rollback frontend ini; tidak ada schema migration atau perubahan data aplikasi dari deployment.


Post-deploy: **enam browser journeys nyata PASS** (50, 51, 47, 156, 123 standalone + 51 dengan before50), melalui UI publik tanpa memilih dropdown untuk standalone/batch inference. 156 memakai CSV-first. Semua menghasilkan workspace READY, scoped case benar, audio Range 206, attention/Keep in mind, Home tanpa future highlights, dan tanpa pageerror/overflow 1280 px; context offset 50→51 tetap 120003 ms. Satu request audio 47 dari Playwright mengalami read timeout pada attempt pertama; curl independen menerima 206/128 bytes, health tetap normal, lalu fresh-browser replay workspace yang sama lulus. Harness resume juga diperbaiki agar login MOCK tidak hilang akibat hard navigation; tidak ada perubahan aplikasi tambahan untuk retry ini.

Enam workspace QA bernama prefix unik `E2E importfix` dihapus dalam transaksi dengan UUID + exact-name guards, row-count harus tepat enam. Workspace pengguna tidak dihapus/reprocess. Private evidence lokal: `outputs/import-fix/` (reproduction, dry-run/VM reports, logs/screenshots, cleanup). Vite lokal yang dimulai untuk QA telah dihentikan; stack VM tetap berjalan. Hosted CI executable belum tersedia; hasil di atas scoped demo verification, bukan domain/provider benchmark atau G-DELIVERY.
