# Baseline scope — Phase 0

Tanggal: 8 Oktober 2026. Dasar: PRD v1.0, implementationPhases, rules, ADR 0001, dan instruksi pengguna untuk Phase 0–1. Kontrak executable baseline: 1.0.0.

## Selected scope

- Q-01: replay offline research; future FR-19/20 tetap di luar v1. Makna offline adalah rekaman historis, bukan local inference.
- Q-02: default Gemini Developer API; target Interactions dan `store=false` mengikuti PRD. Interface provider tidak bergantung pada SDK. Ketersediaan model `gemini-3.8-flash`, API/features, quota, terms dan profile efektif masih UNVERIFIED. Tidak ada fallback diam-diam.
- Google STT V2 inline adalah baseline; model/locale/region/recognizer harus diverifikasi pada Phase 7. Batas chunk awal ≤50 detik dan <10 MB diperiksa kembali sebelum adapter nyata.
- P0 dipertahankan seluruhnya. FR-14/15 P1 tetap scheduled pada 9.5/13.3; tidak deferred, tidak tersedia pada baseline.
- SQLite filesystem lokal, satu API writer; worker terpisah tanpa akses DB. Baseline tidak menambah service/database lain.
- Baseline menggunakan fiktif/sintetik. Domain validation, partner access dan izin corpus nyata belum tersedia.

## Disposition compatibility

Tree awal: dokumentasi dan `.gitkeep`, tanpa app/manifests/tests executable. Source historis tidak direstore. Semua modul aplikasi adalah build-new; dokumentasi/struktur dan batas produk dipakai ulang.

Historical app.py/models.py/session.py/simulator.py/detection.py/storage.py/review.py/reporting.py/scenarios.py adalah referensi historis saja. Paket A mencatat old route/operator-key/wire mapping dan migration/deprecation tests jika compatibility tersebut dipertahankan. IDs/events/frames/commands yang diterima importer archive harus dipertahankan; baseline tidak menyatakan old archive migration sudah diimplementasikan. Training routes tidak menjadi AI tools. Branch/what-if tetap opsional.

PRD §40.3 sebelumnya menyebut vertical slice sebagai arah lama dan kini diselaraskan; execution sequencing yang berlaku adalah roadmap: baseline → A/B independen → integrasi akhir Phase 10. Tidak menjalankan integration slice lintas paket sebelum Phase 10.

## External dependency register

| ID | Dependency | Owner-function | Dibutuhkan sebelum | Dampak dan next action | Closure evidence |
| --- | --- | --- | --- | --- | --- |
| EXT-01 | GCP project/billing/identity/region/locale/recognizer/quota/budget | Cloud operator | 7.4 / G-BE | Belum tersedia; inventaris metadata aman dan lakukan smoke berizin pada Phase 7 | Real synthetic STT request, profile/version/usage |
| EXT-02 | Gemini model/API/key/tier/quota/budget/terms | Cloud operator | 8.5 / G-BE | UNVERIFIED; cek model/features sebelum adapter dipakai, keputusan diperlukan jika target unavailable | Real structured intent/tool smoke dan profile |
| EXT-03 | Corpus local/cloud/export/retention rights | Data owner | Pemrosesan corpus terkait | Jangan download/transfer corpus; sintetik dapat lanjut | Source-specific permission profile |
| EXT-04 | Simulator mitra/layout/clock/coverage | Partner/domain lead | Partner fidelity evaluation | Belum confirmed; gunakan fiktif/sintetik | Authorized export + fidelity/timebase report |
| EXT-05 | VM/domain/TLS/network/operator/budget | Deployment owner | Phase 17 | Tidak menghalangi baseline; siapkan preflight pada delivery | Preflight nyata |
| EXT-06 | Encrypted off-host backup target/operator | Operations owner | G-DELIVERY | Local disposable recovery dapat dibangun dahulu | Off-host backup + isolated measured restore |
| EXT-07 | ATCO reviewer/study consent | Research/domain owner | Domain validation | Technical release wajib NOT_DOMAIN_VALIDATED | Reviewer/protocol/results/disagreements |
| EXT-08 | Intended use/ANSP/assurance/regulator | Organisasi berwenang | Future operational project | Di luar v1; bukan activation gate otomatis | Keputusan/izin tahap tersendiri |

Individu owner belum ditetapkan. Tidak memeriksa file secrets, menghubungi provider, atau menganggap credential dari mesin tersedia. Dependencies ini tidak menghalangi contract foundation; tidak dihapus oleh MOCK pass.
