# Status Implementasi ATC FlowLens

- **Pemeriksaan source/build terakhir:** 5 Oktober 2026
- **Progress FE-01 dan FE-02 diperiksa:** 5 Oktober 2026
- **Cakupan:** source/config/docs sebelumnya ditambah implementasi adapter frontend FE-01/FE-02
- **Metode:** `npm run typecheck` dan `npm run build` di `frontend/` lulus setelah perubahan FE-02. Backend/API runtime, WebSocket runtime, adapter/browser tests, domain review, dan validasi operasional tidak dijalankan.

Dokumen ini mencatat apa yang tampak tersedia di source pada tanggal pemeriksaan. Keberadaan source bukan bukti bahwa komponen berhasil dibangun, berjalan, lulus test, ditinjau trainer, atau tervalidasi untuk operasi.

## Ringkasan

| Area | Status dari inspeksi source | Batas klaim |
|---|---|---|
| Backend | Modul FastAPI, model kontrak, simulasi, deteksi, sesi, review, laporan, dan arsip SQLite tersedia di `backend/`. | Belum diverifikasi saat runtime. |
| API dan stream | Source mendefinisikan route health, skenario, autentikasi operator, sesi, seat, command, event, assessment, review/branch, report, dan WS direct snapshot. FE-02 memakai metadata/snapshot/events/commands/stream yang ada dan menyediakan decoder untuk profil source/assist. | Route source belum diuji runtime. Historical frame-at-time dan route replay/assist additive SC-06 belum ada di backend source; decoder/opt-in mock path FE tidak membuktikan dukungan server. |
| Persistensi | Source `backend/storage.py` menyediakan arsip SQLite untuk metadata, event, snapshot, checkpoint, dan command. | Belum ada hasil uji recovery, durability, beban, atau concurrency dalam pemeriksaan ini. |
| Frontend | Source FE-01 mencakup `App.tsx`, `styles.css`, typed adapter contracts, `FixtureReplayReviewAdapter`, dan `ApiDashboardAdapter`. FE-02 menambah `ApiReplayReviewAdapter`, runtime decoder, scoped credential handling, error states, event cutoff, command time conversion, WS first-message auth, sequence guard/resync/reconnect, cancellation, dan unavailable untuk route additive. `npm run typecheck` serta `npm run build` lulus pada 5 Oktober. | REST/WS runtime dan QA tests belum dijalankan. Backend saat ini tidak menerbitkan credential source-read/reviewer terpisah. Historical frame dan endpoint assist belum ada. |
| Penyajian UI | `backend/app.py` menyajikan bundle dari `frontend/dist`; `npm run build` pada 5 Oktober menghasilkan `dist/index.html` di workspace (direktori ini di-ignore Git). | Backend startup dan route `/` belum diuji. Checkout bersih tetap perlu menjalankan build sebelum bundle tersedia. |
| Test dan validasi manusia | Tidak ditemukan direktori `tests/` atau hasil test pada pemeriksaan ini. | Tidak ada klaim test lulus, review trainer, studi peserta, sertifikasi, atau manfaat keselamatan tervalidasi. |
| AI advisory replay | Requirement target mencakup replay offline simulator mitra, transkripsi/evidence, dan kandidat opsi AI yang ditinjau evaluator. Baseline sintetik boleh dipakai sebelum akses mitra tersedia. Frontend kini memiliki decoder/read-model/adapter boundary untuk transcript, evidence, jobs, dan options. | Route worker/assist/audio store dan provider belum ada di backend source; route additive FE menghasilkan `unavailable` sampai implementasi server tersedia. Belum ada mitra/replay berizin yang dikonfirmasi, domain review, atau validasi operasional. |

## Arsitektur target yang didokumentasikan

Rencana Teknis MVP menetapkan satu proses server lokal/LAN sebagai pemilik state sesi, frontend browser React/TypeScript, REST untuk command dan arsip, WebSocket untuk snapshot sinkron, Shapely untuk geometri, serta SQLite lokal untuk persistence. Alur target memisahkan truth simulator dari observasi yang diterima detector, lalu membentuk prediksi occupancy dan alert yang menyertakan evidence serta kualitas data. Sesi ditujukan untuk latihan multi-peran, replay, dan debrief.

Arsitektur tersebut adalah target spesifikasi. Rincian acceptance dan batas MVP berada di [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md); kode aktual perlu diperiksa terpisah sebelum menyatakan bagian target telah selesai.

## Batas produk yang berlaku

- Arah produk jangka panjang adalah advisory berbukti bagi controller Tower/Ground runway; target MVP tetap replay offline, bukan live ATC.
- FlowLens tidak menerbitkan clearance dan tidak mengambil alih keputusan controller.
- Replay simulator mitra yang berizin menjadi target validasi fidelity. Baseline sintetik sementara tidak membuktikan realisme operasional. Transkripsi, kandidat opsi AI, adapter replay, dan UI review belum terbukti ada di source. Live integration, persetujuan/assurance, dan klaim manfaat keselamatan belum dicapai.
- Indikator kompleksitas/workload adalah konteks eksperimen, bukan diagnosis kondisi mental atau ukuran fitness-for-duty.

## Memperbarui status

Perbarui tanggal dan tabel ini setelah ada perubahan implementasi atau verifikasi yang berarti. Sebutkan command/check yang benar-benar dijalankan dan hasilnya. Pisahkan status source, build, runtime, automated test, domain review, dan operational validation; jangan gabungkan menjadi satu label “selesai”.
