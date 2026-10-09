# Modular Repository Layout and Private Data Boundaries

| Atribut | Nilai |
| --- | --- |
| Status keputusan | Accepted |
| Tanggal | 7 Oktober 2026 |
| Status implementasi | Directory scaffold tersedia; modul dan runtime belum diimplementasikan |

## Context

Tree proyek telah direset dengan mempertahankan kontrak produk dan roadmap di `.agent/`. Implementasi baru membutuhkan tempat yang jelas untuk FastAPI, worker Google STT/Gemini, frontend React, kontrak wire, tests, evaluator labels, dokumentasi, dan delivery tooling.

Scaffold harus memudahkan pengembangan bertahap tanpa menjadikan folder kosong sebagai klaim fitur selesai. Evaluator truth dan private runtime data juga membutuhkan boundary yang terlihat sejak penempatan file.

## Decision

Repository menggunakan satu workspace dengan package Python `backend/flowlens/`, frontend `frontend/`, dan modul berdasarkan responsibility. Backend tetap modular monolith dengan satu API writer, bukan kumpulan microservices.

Frontend menggunakan feature folders. Generated wire artifacts berada di `contracts/` dan generated TypeScript client berada di `frontend/src/api/generated/`; schema Pydantic backend tetap menjadi authority, bukan schema duplikat yang diedit terpisah.

Tests/fixtures publik yang aman berada di `tests/`. Labels/oracles/protocol evaluator berada di `evaluation/`, di luar package produksi. Pemisahan folder tidak menggantikan runtime permission, import boundary, atau truth-isolation tests.

Dokumentasi berada di `docs/`, dengan ADR di `docs/adr/`. Reserved deployment/scripts/workflow directories disiapkan, tetapi file executable, Dockerfiles, Compose, dan CI ditambahkan pada tahap yang sesuai. Empty leaf directories ditrack melalui `.gitkeep`.

Private storage menggunakan `data/` untuk DB, assets, exports, scratch, backups, logs, dan secrets. Temporary validation artifacts menggunakan `artifacts/`. Payload kedua area serta evaluator report outputs di-ignore; hanya directory placeholders yang masuk Git.

## Rationale and Alternatives

Feature/responsibility modules mengikuti alur import–replay–audio–intent–memory–advisory dan mengurangi ketergantungan pada satu app file besar. Package namespace `flowlens` juga menghindari penggunaan nama generik `backend` sebagai identitas package aplikasi.

Pemisahan microservices atau shared polyglot package ditunda karena v1 memakai satu VM/single-writer SQLite. Layer berulang yang dibuat untuk setiap fitur juga tidak diwajibkan; folder dapat dipecah ketika tanggung jawab memang bertambah.

Menaruh evaluator labels di package detector ditolak karena meningkatkan risiko truth leakage. Menaruh runtime audio/DB pada tracked fixtures ditolak karena mengaburkan provenance dan hak redistribusi.

## Implementation Details and Consequences

Backend routes memanggil services/domain melalui composition yang eksplisit. Worker memakai DTO/ports dan internal API; tidak mengimpor storage writer atau membuka SQLite. Detector memakai observations/geometry/rules, bukan evaluator labels, future schedule, atau provider state.

Frontend memakai API/WS; tidak membaca SQLite, secret files, raw provider responses, atau evaluator truth. `frontend/public/` hanya untuk static assets publik, bukan audio privat atau export.

Scaffold tidak menambahkan manifests, dependency versions, Python `__init__.py`, app entrypoints, script stubs, atau workflow yang tampak executable. Folder deployment/frontend kosong tidak mengubah gate backend-first yang sudah ditetapkan.

## Validation

Verifikasi struktur mencakup placeholder kosong pada leaf directories, Markdown links, pemetaan modul/fitur ke PRD, serta aturan ignore: runtime/secret payload di-ignore sementara `.gitkeep` dapat ditrack. Commit tree harus memuat hanya scaffold, dokumentasi, dan perubahan konteks yang diizinkan.

Tidak ada build/runtime/provider/domain test yang diklaim oleh validasi struktur. Import boundaries, API contracts, authorization, and truth isolation harus dibuktikan saat kode tersedia.

## Risks and Follow-Up

Folder yang lengkap dapat memberi kesan produk sudah tersedia; status scaffold harus tetap terlihat pada README/handoff. Docs dan ADR tidak dapat memaksakan boundary kode tanpa tests.

Fondasi backend berikutnya menetapkan runtime/dependency locks, actual module contracts, migrations, dan executable tests. Frontend implementation menunggu G-BE; containerization dan deployment menunggu G-FE.
