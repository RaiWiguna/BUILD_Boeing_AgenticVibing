# Prompt kerja modular — `feat/frontend`

Gunakan prompt ini saat melanjutkan pengembangan frontend ATC FlowLens. Sesuaikan ID task FE dengan pekerjaan yang diminta.

```text
Kamu mengerjakan ATC FlowLens pada branch `feat/frontend`, yang dibuat dari `dev`.

Tujuan kerja: bangun frontend React/TypeScript secara modular dan data-driven. UI harus memakai adapter bertipe, dan mode API harus melakukan fetch ke backend lokal yang tersedia. Jangan mengganti fetch yang gagal dengan fixture atau data palsu.

Batas branch dan ownership:
- Kerjakan hanya file frontend yang dimiliki FE, terutama `frontend/src/`, konfigurasi/package FE bila diperlukan, serta dokumen status yang relevan.
- Biarkan perubahan backend pada `feat/backend`. Jangan checkout, cherry-pick, merge, atau mengubah branch/file backend untuk membuat frontend berjalan.
- Kerjakan terhadap shared contracts, API source yang memang sudah ada pada branch, fixture public, dan typed adapters. Dependency lintas workstream boleh memakai adapter/transport mock.
- Integrasi kedua workstream dilakukan kemudian lewat `dev`; jangan merge branch selama tugas implementasi FE.

Acuan:
1. Baca `AGENTS.md` dan `docs/README.md`.
2. Baca [Technical Implementation](README.md), shared contracts yang relevan, dan packet/task FE yang diminta.
3. Gunakan source backend hanya untuk memeriksa route/wire yang sudah ada. Dokumen status adalah inventaris, bukan bukti build atau runtime.
4. Pisahkan CURRENT_SOURCE, TARGET, PROPOSED_CONTRACT, ASSUMPTION, dan UNKNOWN.

Arsitektur frontend:
- Komponen React membaca read-model/port; komponen tidak melakukan `fetch` langsung dan tidak mengimpor database, storage privat, provider AI, atau fixture rahasia.
- `VITE_FLOWLENS_MODE=fixture|api` memilih adapter secara eksplisit. `fixture` adalah authored synthetic baseline yang selalu diberi label `SYNTHETIC / NOT OPERATIONALLY VALIDATED`. `api` melakukan fetch same-origin melalui `/api` dan Vite proxy yang sudah dikonfigurasi.
- Kegagalan koneksi/auth/schema pada mode `api` tetap ditampilkan sebagai disconnected/unauthorized/error. Jangan mengganti source ke fixture diam-diam.
- Token hanya berada di memori tab dan header Authorization; jangan menulis token/key ke URL, localStorage, sessionStorage, atau bundle.
- Decode respons runtime sebelum membuat read-model. Tolak shape/profile yang tidak dikenal; jangan mengandalkan `as` cast sebagai validasi.
- Source observation, prediction, event, transcript mentah/koreksi, dan kandidat AI tetap kategori berbeda. Jangan hitung ulang severity/confidence di UI.
- Kandidat AI hanya untuk replay evaluator; tidak boleh ada aksi send/execute/clearance dari kandidat. Tidak ada production feed, live audio capture, atau rekomendasi untuk posisi kontrol aktif.

Pengerjaan:
- Implementasikan hanya task FE yang diminta dan dependency FE sebelumnya. Pertahankan ownership file dari packet; QA memiliki file test/fixture executable di namespace `tests/`.
- FE-01 membangun shell, typed ports, fixture adapter, dan API bootstrap untuk endpoint existing. FE-02 memperluas transport untuk replay/assist, auth scope, decoder, paging, cancel, dan reconnect; FE-03–05 mengembangkan UI map, timeline, evidence, dan review.
- Perbarui task packet, technical blueprint, dan `docs/IMPLEMENTATION_STATUS.md` secukupnya saat status source atau verifikasi berubah. Jangan menyebut source sebagai built, running, test-passing, domain-reviewed, atau operationally validated tanpa bukti masing-masing.
- Laporkan branch, file yang diubah, command pemeriksaan yang benar-benar dijalankan, dan batas yang masih belum diverifikasi. Jangan mengklaim integrasi dengan perubahan `feat/backend` sebelum diuji bersama pada `dev`.
```

Status konteks prompt: pada 5 Oktober 2026, branch `feat/frontend` memuat implementasi awal FE-01 dan API bootstrap untuk route synthetic-training existing. API replay/assist adapter penuh serta FE-03–05 masih pekerjaan berikutnya.
