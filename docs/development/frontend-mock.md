# Frontend MOCK — panduan pengembang

Tanggal: 9 Oktober 2026. Status: MOCK track (Phase 11–13 `in_progress (MOCK)`); G-FE tetap `blocked` sampai G-BE `passed` dan journeys dijalankan terhadap backend nyata. Rencana dan keputusan: [frontend implementation plan](frontend-implementation-plan.md). Evidence: [frontend MOCK evidence](../testing/frontend-mock-evidence.md). Skrip demo: [demo frontend MOCK](../demo/frontend-mock-demo.md).

## Menjalankan

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # tsc + vite build ke frontend/dist
npm run preview    # http://localhost:4173, build produksi
```

Semua data `SYNTHETIC` + `MOCK` dilayani adapter in-browser; tidak ada backend, provider, file audio, atau secret. Refresh halaman me-reset data mock (review, export, brief baru); login tetap per tab (sessionStorage).

| Akun demo | Role | Catatan |
| --- | --- | --- |
| `evaluator@flowlens.test` | Evaluator | Review, brief, export |
| `controller@flowlens.test` | Controller review | Review tanpa export |
| `observer@flowlens.test` | Observer | Read-only |
| `admin@flowlens.test` | Administrator | Settings admin |
| `tyler@flowlens.test` | — | Nonaktif (login ditolak) |

Password semua akun demo: `flowlens-demo` (hanya untuk mock lokal). Kartu **MOCK demo accounts** di halaman login mengisi email; menu akun (kiri bawah) mengganti role dan membersihkan cache.

Tombol **Mock** (kanan bawah) mensimulasikan kondisi server: provider outage, connection lost, conflict on next save, audio access denied, stale tracks, empty catalogue, disk 91 %, sign-in expired, serta latency. Flag disimpan di memori; full page load me-reset-nya.

## Struktur singkat

| Lokasi | Isi |
| --- | --- |
| `src/api/client.ts` | Port `ApiClient` dan `StreamClient` — satu-satunya API yang dipakai layar |
| `src/api/types.ts`, `src/api/generated/` | Tipe kontrak 1.0.0 (generated) dan view DTO berlabel `PROPOSED_CONTRACT` |
| `src/api/adapters/mock/` | `MockApiClient` (simulasi perilaku server: as-of, authz, idempotency, `expectedVersion`, append-only, stale) dan seed skenario |
| `src/app/providers/ApiProvider.tsx` | Wiring adapter |
| `src/features/*` | Layar per area; ESLint melarang `features` mengimpor `adapters` |

## Mengganti ke HTTP adapter (setelah G-BE)

1. Implementasikan `ApiClient` di `src/api/adapters/http/` memakai client dari OpenAPI kontrak yang dibekukan, dan `StreamClient` WebSocket untuk `/sessions/{id}/stream`.
2. Reconcile setiap tipe `PROPOSED_CONTRACT` di `src/api/types.ts` dengan kontrak backend (versi baru bila breaking); jalankan `npm run gen:types` dan `npm run check:types`.
3. Ganti `value` di `ApiProvider.tsx` ke adapter HTTP. Layar tidak berubah.
4. Hapus panel Mock dari `AppShell` (`devtools` di `routes.tsx`) dan kartu akun demo di login; label `MOCK` hilang, label `SYNTHETIC` tetap selama datanya sintetik.
5. Jalankan ulang Vitest dan journeys Playwright terhadap stack nyata; baru setelah itu G-FE dapat dinilai.

## Checks

```bash
cd frontend
npm run typecheck
npm run lint
npm run check:types
npm run check:copy
npm test
npm run build
```

Journeys MOCK (Python Playwright, opt-in; skip bila Playwright atau server tidak tersedia):

```bash
uv add --dev pytest-playwright
FLOWLENS_FRONTEND_URL=http://localhost:4173 uv run pytest tests/e2e/frontend_mock --browser-channel chrome
```

`--browser-channel chrome` memakai Chrome lokal; tanpa itu jalankan `uv run playwright install chromium` dulu. Journeys hanya berjalan terhadap `localhost`/`127.0.0.1`.
