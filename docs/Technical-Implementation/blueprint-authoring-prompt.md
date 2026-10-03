# Prompt Penyusunan Technical Implementation Blueprint FlowLens

Salin prompt berikut saat meminta coding agent menyusun paket dokumentasi implementasi teknis FlowLens. Prompt ini menghasilkan dokumentasi, bukan mengimplementasikan source code.

```text
Kamu adalah technical documentation architect untuk ATC FlowLens di repository BOEING BUILD.

TUJUAN
Susun Technical Implementation Blueprint yang cukup rinci agar beberapa engineer dapat mengerjakan paket teknis secara modular dan paralel, lalu mengintegrasikannya melalui kontrak yang jelas. Fokus hanya pada arsitektur teknis, alur data/kerja, batas modul, antarmuka, mock/fixture, tujuan dan output tiap paket, serta verifikasi teknis.

BATAS PRODUK YANG MENJADI KONTEKS
- Tujuan jangka panjang: advisory berbukti bagi controller Tower/Ground runway; controller tetap memegang keputusan dan clearance.
- MVP saat ini: replay offline dari simulator training mitra dengan candidate options AI hanya untuk evaluasi. Periksa dokumen status untuk konfirmasi mitra/data terbaru.
- Bila replay mitra belum tersedia, synthetic baseline dapat dipakai untuk pengembangan dan uji repeatability, tetapi tidak membuktikan fidelity operasi.
- Jangan mengarahkan implementasi MVP ke live VHF, production feed, atau rekomendasi pada posisi kontrol aktif. Tujuan live adalah konteks arsitektur masa depan, bukan izin untuk integrasi.

SUMBER KONTEKS — BACA SELEKTIF
1. Baca AGENTS.md dan docs/README.md untuk aturan proyek dan otoritas dokumen.
2. Gunakan docs/IMPLEMENTATION_STATUS.md serta source aktual untuk menyatakan kondisi CURRENT. Verifikasi source yang relevan, terutama backend/ dan frontend/; jangan menganggap daftar file lama masih akurat.
3. Gunakan docs/Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md untuk target simulator, data/time, detector, replay, dan acceptance.
4. Gunakan docs/Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md untuk target replay offline dan batas AI harness.
5. Gunakan docs/Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md hanya untuk konteks domain dan evidence yang relevan. Jangan mengubah temuan atau asumsi domain menjadi kontrak teknis tanpa dasar.
6. Untuk contoh struktur packet, gunakan secara selektif D:\Kuliah\KP\Intern_ProjectWebPTPI\.agents\implementation\BE-01-backend-foundation.md, BE-07-ai-deterministic-workflow.md, serta docs/backend/08-api-contract.md dan docs/backend/10-frontend-integration.md pada proyek contoh. Ambil pola objective, scope/context, implementation contract, output, dan verification saja. Jangan salin domain SmartPlan atau proses approval/gate proyek tersebut. Jika path contoh tidak tersedia, lanjutkan dengan format packet yang dijelaskan di prompt ini.

STATUS DAN BAHASA KLAIM
- Bedakan CURRENT_SOURCE, TARGET, ASSUMPTION, UNKNOWN, dan PROPOSED_CONTRACT.
- Source yang ada bukan bukti build/runtime/test berhasil. Jangan menyatakan target sudah diimplementasikan hanya karena tertulis dalam dokumen.
- Tandai interface yang ditemukan di source berbeda dari interface target yang Anda usulkan.
- Gunakan bahasa Indonesia untuk uraian; pertahankan identifier, nama tipe, istilah API, dan nama file dalam bentuk teknis aslinya.

OUTPUT DOKUMEN
Buat dokumentasi baru di docs/Technical-Implementation/ dengan struktur berikut:

1. README.md — master blueprint dan indeks paket. Ringkas system boundary, CURRENT vs TARGET, peta subsistem, alur replay end-to-end, matrix paket/owner-role/output/interface, serta peta dependensi/integrasi.
2. shared-contracts.md — kontrak lintas paket yang diperlukan untuk bekerja paralel: session/replay event, timebase/provenance/quality, backend ports dan API/stream yang relevan, AI harness input/output, frontend adapter/read model, versioning, serta contoh mock/fixture minimum. Turunkan struktur tepat dari source dan spesifikasi; jangan mengarang fields atau wire shape yang tidak diperlukan.
3. packages/backend-session-replay-storage.md — ownership session/replay import, persistence/archive, API/stream, serta integrasi dengan event source dan detector.
4. packages/simulation-detection.md — simulation clock, scenario/observations, deterministic geometry/prediction/rules, evidence, dan kualitas data.
5. packages/ai-harness.md — offline audio/replay input, ASR/transcript, candidate entities, evidence reconciliation, evaluator-only option candidates, provenance, worker boundary, dan failure/degraded states.
6. packages/frontend-replay-review.md — typed UI boundary, replay timeline, map/runway context, transcript/evidence review, candidate options, mock adapter, dan UI states.
7. packages/integration-qa.md — contract fixtures/tests lintas paket, integration scenario, cara menjalankan mock stack, offline packaging boundary, dan checks teknis.

Tambahkan tautan ke master blueprint pada docs/README.md. Jangan menulis ulang dokumen spesifikasi kanonis atau implementation status; cukup referensikan dan catat konflik teknis bila ditemukan.

MODEL KERJA MODULAR
- Gunakan shared contract sebagai satu-satunya prasyarat desain bersama. Semua workstream lain harus dapat memulai pengembangan dengan mocks/stubs yang mengikuti kontrak tersebut; jangan membuat paket menunggu implementasi paket lain jika mock kontraknya cukup.
- Dalam master, bedakan contract dependency (interface yang harus sama), runtime dependency (komponen yang berinteraksi saat berjalan), dan integration check (yang baru dapat diuji setelah implementasi digabung). Jangan menyamakan ketiganya dengan urutan kerja serial.
- Paket integrasi/QA boleh menyelesaikan contract tests dan fixture lebih awal; end-to-end runtime dilakukan setelah komponen tersedia.
- Buat dependency map tanpa siklus. Untuk setiap ketergantungan, nyatakan apakah paket dapat berjalan dengan stub, data fixture, atau perlu output runtime riil hanya untuk verifikasi integrasi.
- Tiap file/modul source yang diubah di masa implementasi harus punya satu workstream owner-role. Jika ownership existing belum jelas, tunjukkan boundary dan usulkan file baru tanpa menimpa file milik paket lain.
- Gunakan owner-role seperti Backend/Replay, Simulation/Detection, AI Harness, Frontend, dan Integration/QA; jangan mengarang nama anggota atau ukuran tim.

TEMPLATE WAJIB UNTUK SETIAP PACKAGE
- ID/nama paket dan owner-role.
- Objective dan output yang dapat diserahkan ke paket lain.
- CURRENT/TARGET serta scope included/excluded.
- Context packet: hanya dokumen/source/test yang relevan, dengan path aktual.
- Modul/file ownership dan batas terhadap paket tetangga.
- Inputs, outputs, kontrak yang dikonsumsi/dihasilkan, serta consumer.
- Mock/stub/fixture yang memungkinkan pengerjaan dan test mandiri.
- Alur utama dan failure/degraded cases yang relevan.
- Verification teknis/acceptance agar hasil siap dihubungkan; ini bukan approval atau sign-off.
- Asumsi dan unknown teknis ringkas, ditulis langsung dalam packet terkait.

KONTRAK DAN PEMISAHAN LAYER
- Pastikan source replay, event/session time, receive time, source identity, provenance, missing/stale quality, dan candidate AI tidak tercampur menjadi satu nilai tanpa asal.
- Pisahkan authoritative simulator/session event dari derived detector result dan AI candidate output.
- Kandidat AI hanya ada dalam replay/evaluator context, harus menunjuk evidence/uncertainty, dan tidak membawa command/clearance action.
- Frontend membangun terhadap typed interface/mock, bukan langsung mengikat page ke file/storage/backend implementation.
- Simulation/detection dan AI harness dapat diuji sendiri dari canonical fixtures; integrasi menggunakan kontrak yang sama.
- Jika API existing belum menyediakan kebutuhan target, tandai sebagai proposed additive contract. Jangan menyatakan API telah berubah atau membuat source code.

YANG TIDAK DIMINTA
- Jangan membuat product strategy/PRD baru, business case, approval workflow, design sign-off, approval log, ADR register, formal review board, release-gate bureaucracy, atau pencatatan persetujuan stakeholder.
- Jangan membuat jadwal, estimasi biaya, nama/person allocation, atau target numerik yang tidak diminta/didukung.
- Jangan menjalankan atau mengubah source code, API, schema runtime, migration, test, dependency, atau deployment. Tugas ini dokumentasi teknis saja.
- Jangan menyalin penuh .agents atau seluruh docs proyek contoh. Ambil hanya struktur packet dan pola pemisahan contract/interface yang diperlukan.

VERIFIKASI DOKUMEN
Sebelum selesai, periksa bahwa:
1. seluruh path/tautan lokal di blueprint valid dan master mengindeks semua packet;
2. tidak ada dua paket yang memiliki file/API/type yang sama tanpa boundary eksplisit;
3. dependency map acyclic dan paket selain shared contract dapat mulai menggunakan stub/mock;
4. setiap package memiliki objective, output, interface, mock/test, dan readiness-to-integrate criteria;
5. CURRENT/TARGET/ASSUMPTION/UNKNOWN dibedakan dan tidak ada klaim source/build/runtime yang tidak diperiksa;
6. tidak ada approval/sign-off process atau live-operations implementation yang terselip sebagai kewajiban MVP.

Gunakan git diff --check dan pemeriksaan tautan Markdown bila tersedia. Jangan menjalankan build atau test aplikasi karena tugas ini tidak mengubah source.

HASIL AKHIR
Simpan hanya blueprint dan packet teknis yang diminta beserta tautan indeks docs/README.md. Laporkan file dokumentasi yang dibuat/diubah, ringkasan pembagian workstream, checks dokumen yang dijalankan, serta CURRENT/TARGET/UNKNOWN penting. Jangan mengklaim implementasi fitur.
```
