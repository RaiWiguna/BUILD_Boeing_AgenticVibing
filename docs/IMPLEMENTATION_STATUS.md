# Status Implementasi ATC FlowLens

- **Pemeriksaan source/build terakhir:** 5 Oktober 2026
- **Progress FE-01 sampai FE-03 diperiksa:** 5 Oktober 2026
- **Cakupan:** source/config/docs sebelumnya ditambah typed adapter FE-01/FE-02 dan source context, runway map/board, deterministic evidence UI FE-03
- **Metode aktual setelah FE-03:** `npm run typecheck` dan `npm run build` di `frontend/` lulus. Backend/API runtime, WebSocket runtime, browser QA, domain review, dan validasi operasional tidak dijalankan.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, model kontrak, simulasi, deteksi, sesi, review, laporan, dan arsip SQLite tersedia di `backend/`. | Belum diverifikasi saat runtime. |
| API dan stream | Source mendefinisikan route health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, dan WS direct snapshot. FE-02 memakai metadata/snapshot/events/commands/stream yang ada dan menyediakan decoder untuk profil source/assist. | Route source belum diuji runtime. Historical frame-at-time dan route replay/assist additive SC-06 belum ada di backend source; decoder/opt-in mock path FE tidak membuktikan dukungan server. |
| Persistensi | Source `backend/storage.py` menyediakan arsip SQLite untuk metadata, event, snapshot, checkpoint, dan command. | Belum ada hasil uji recovery, durability, beban, atau concurrency dalam pemeriksaan ini. |
| Frontend | FE-01/FE-02 menyediakan `ReplayReviewAdapter`, fixture/API adapter, runtime decoder, scoped credential handling, review controls dan subscription handling. FE-03 menambah source context, SVG `LOCAL_METRES` map dari layout, runway board, observed/last-known track labels, prediction windows, dan deterministic alert evidence/ack panel yang memakai adapter/read model. `npm run typecheck` dan `npm run build` lulus pada 5 Oktober setelah FE-03. | REST/WS runtime dan browser QA belum dijalankan. Backend tidak menerbitkan credential `source_read` terpisah; operator token tidak dipakai pada port tersebut. Historical frame-at-time dan route replay/evidence/assist additive belum ada di backend source. |
| Penyajian UI | `backend/app.py` menyajikan bundle dari `frontend/dist`; `npm run build` setelah FE-03 menghasilkan `dist/index.html` dan asset lokal (direktori `dist/` di-ignore Git). | Backend startup, route `/`, dan browser runtime belum diuji. Checkout bersih tetap perlu menjalankan build sebelum bundle tersedia. |
| Test dan validasi manusia | FE-03 tidak menulis file pada namespace `tests/`. Dua command frontend yang diminta (`npm run typecheck`, `npm run build`) lulus; QA/browser suite tidak dijalankan. | Tidak ada klaim test browser lulus, review trainer, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| AI advisory replay | Requirement target mencakup replay offline simulator mitra, transkripsi/evidence, dan kandidat opsi AI yang ditinjau evaluator. Baseline synthetic FE-03 diberi label belum tervalidasi operasional. Frontend menyediakan read-model/adapter boundary dan panel deterministic evidence; source evidence ditampilkan hanya setelah resolve ID pada source scope. | Route worker/assist/audio store dan provider belum ada di backend source; route additive FE tampil unavailable sampai implementasi server tersedia. Belum ada mitra/replay berizin yang dikonfirmasi, domain review, atau validasi operasional. |

## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- Arah produk jangka panjang adalah advisory berbukti bagi controller Tower/Ground runway; target MVP tetap replay offline, bukan live ATC.
- FlowLens tidak menerbitkan clearance dan tidak mengambil alih keputusan controller.
- Replay simulator mitra yang berizin menjadi target validasi fidelity. Frontend replay adapter serta source/map/deterministic-evidence UI tersedia di source; baseline sintetik tetap tidak membuktikan realisme operasional. Worker transkripsi/provider dan route/flow kandidat opsi AI belum tersedia sebagai runtime backend. Live integration, persetujuan/assurance, dan klaim manfaat keselamatan belum dicapai.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
