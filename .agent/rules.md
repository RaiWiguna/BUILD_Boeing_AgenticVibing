# Aturan Coding Agent — ATC FlowLens

| Atribut | Nilai |
| --- | --- |
| Status | Aktif untuk pekerjaan repository; requirement target tetap dibedakan dari implementasi |
| Tanggal | 7 Oktober 2026 |
| Tujuan | Menjaga kesinambungan keputusan produk, implementasi, verifikasi, dan handoff |
| Cakupan | Pekerjaan source, test, dokumentasi, data, AI, serta deployment ATC FlowLens |

Kata **wajib**, **dilarang**, **sebaiknya**, dan **dapat** menetapkan tingkat kewajiban. Instruksi eksplisit pengguna berlaku di atas aturan proyek ini. Jangan membuat approval tambahan untuk pekerjaan rutin yang sudah diizinkan. Jika ada konflik yang memengaruhi scope atau kewenangan produk, jelaskan konflik dan minta keputusan sebelum melakukan perubahan yang bergantung padanya.

## 1. Tujuan Folder `.agent/`

Folder ini menyimpan kontrak produk dan konteks eksekusi lintas sesi agar keputusan tidak terus dibuat ulang.

- Pertahankan keputusan stack, batas produk, requirement, dan acceptance criteria.
- Bedakan target, implementasi yang ditemukan, serta hasil pemeriksaan yang dijalankan.
- Simpan handoff dan status roadmap secara ringkas ketika fasilitas tersebut digunakan.
- Catat keputusan arsitektur yang tahan lama beserta alasan dan konsekuensinya.
- Jangan menjadikan folder ini tempat scratch output, credential, audio, atau salinan seluruh dokumentasi.

## 2. Urutan Membaca Konteks

Untuk memulai pekerjaan:

1. Baca `AGENTS.md` dan `docs/README.md` terlebih dahulu.
2. Baca `.agent/rules.md`.
3. Baca bagian `.agent/PRD.md` yang sesuai dengan tugas, termasuk requirement dan acceptance terkait.
4. Baca `.agent/sessionHandoff.md` dan `.agent/implementationPhases.md` jika tersedia.
5. Muat bagian rencana teknis, AI advisory, shared contracts, atau task packet yang relevan melalui peta dokumen.
6. Periksa source, konfigurasi, dan test pada area yang akan diubah.
7. Baca release checklist, deployment runbook, dan ADR yang relevan jika tersedia dan diperlukan.

Tidak perlu memuat semua dokumen setiap sesi. File opsional yang belum ada bukan blocker dan tidak boleh diperlakukan sebagai bukti bahwa prosesnya sudah berjalan.

## 3. Otoritas dan Status Informasi

| Area | Otoritas dan penggunaan |
| --- | --- |
| Batas proyek dan penggunaan | `AGENTS.md` serta keputusan eksplisit pengguna |
| Target produk, arsitektur, dan core requirements | `docs/Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md` |
| Target AI advisory dan batas replay/live | `docs/Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md` |
| Kontrak v1, stack pilihan pengguna, fitur, data/API, UX, dan acceptance | `.agent/PRD.md` |
| Evidence domain | `docs/Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md`; pertahankan cakupan, tanggal, dan tingkat kepastian |
| Rencana implementasi | Paket yang relevan di `docs/Technical-Implementation/`; rencana bukan bukti implementasi |
| Perilaku saat ini | Source, konfigurasi, dan hasil pemeriksaan yang relevan |
| Inventaris implementasi | `docs/IMPLEMENTATION_STATUS.md`; inventaris bertanggal, bukan pengganti inspeksi source |
| Progress lintas sesi | Handoff dan roadmap jika tersedia |
| Keputusan arsitektur | ADR jika tersedia; status proposed tidak berarti accepted |

Keputusan stack yang sudah ditetapkan pengguna harus dipertahankan. Jika task packet lama masih memakai provider lokal atau kontrak yang berbeda, nyatakan mismatch dan sesuaikan pekerjaan dengan keputusan yang sudah diizinkan; jangan diam-diam menghidupkan kembali pilihan lama.

Kode yang sudah ada tidak otomatis menggantikan target produk. Desain target juga tidak membuktikan perilaku kode. Konflik antarrequirement yang mengubah scope wajib diselesaikan dengan product owner sebelum perubahan yang bergantung padanya dijalankan.

Laporkan status secara terpisah: **ada di source**, **build berhasil**, **berjalan**, **automated tests lulus**, **provider benchmark dilakukan**, **direview pakar domain**, dan **tervalidasi operasional**. Jangan menaikkan status tanpa bukti.

## 4. Batas Produk dan Engineering

### 4.1 Scope dan Kewenangan

- V1 adalah replay offline dengan temuan dan kandidat opsi yang ditinjau evaluator.
- Target data adalah replay simulator mitra berizin. Selama akses belum tersedia, gunakan baseline sintetik yang diberi label belum tervalidasi terhadap operasi.
- Tidak ada mitra atau akses data yang dikonfirmasi pada baseline 3 Oktober 2026. Jangan memperbarui klaim tersebut tanpa bukti baru.
- Controller tetap memegang keputusan dan kewenangan clearance.
- Dilarang menghubungkan feed/audio produksi atau menampilkan advisory pada posisi ATC aktif dalam scope v1.
- Simulasi berjalan, microphone lab, operational shadow, dan live advisory adalah tahap terpisah; jangan menyimpulkan izin dari arah produk jangka panjang.
- Gate live mencakup intended use, izin ANSP/pemilik data, keamanan, human factors, safety assurance, dan kewajiban regulator yang ditentukan bersama organisasi berwenang.
- Output AI tidak boleh mengeksekusi clearance, command simulator, perubahan instruksi sumber, atau tindakan operasional.
- Jangan menyebut temuan AI sebagai verdict keselamatan, memori aplikasi sebagai e-strip resmi, atau indikator komunikasi sebagai diagnosis workload mental.

### 4.2 Stack yang Dipertahankan

| Layer | Keputusan |
| --- | --- |
| Frontend | React, TypeScript, Vite, shadcn/ui; Tailwind untuk styling komponen |
| Server cache frontend | TanStack Query sebagai pilihan engineering awal |
| Backend | Python, FastAPI, Pydantic |
| Transkripsi | Google Cloud Speech-to-Text; konfigurasi V2/model/locale/region dibekukan setelah verifikasi |
| LLM | Gemini 3.8 Flash, target model ID `gemini-3.8-flash` |
| SDK cloud | Adapter berbasis `google-cloud-speech` dan `google-genai` |
| Database | SQLite pada filesystem lokal, dengan satu API writer |
| Geometri | Shapely untuk pemeriksaan deterministik |
| Transport | REST dan WebSocket |
| Deployment | Docker Compose untuk lokal dan satu VM per environment |
| Edge | Caddy untuk static frontend, reverse proxy, dan TLS VM |
| Verifikasi | pytest, Python Playwright, frontend typecheck/build, serta checks sesuai risiko |

Verifikasi model/API pada akun dan konfigurasi efektif sebelum integrasi atau release. Model target dalam PRD tidak membuktikan akses akun, quota, kualitas, atau kompatibilitas fitur. Jika target tidak dapat dipakai, laporkan blocker dan opsi konkret; jangan mengganti provider/model secara diam-diam.

Jangan menambah PostgreSQL, Redis, vector database, Kubernetes, microservices, atau inference lokal sebagai dependency default. Perubahan tersebut memerlukan kebutuhan yang terbukti dan keputusan arsitektur yang sesuai.

### 4.3 Runtime Lokal dan Penyimpanan

- Urutan implementasi wajib mengikuti `.agent/implementationPhases.md`: backend lengkap dan G-BE sebelum frontend; frontend lengkap dan G-FE sebelum containerization aplikasi serta deployment. Contract generation dan tests backend boleh berlangsung sebelum frontend; mocks tidak memberi izin melewati gate.
- Target full stack dijalankan melalui Compose. Selama Compose belum tersedia, gunakan entrypoint yang benar-benar ada dan sebutkan bagian yang belum disediakan.
- Database normal v1 adalah SQLite; jangan mewajibkan database service pada host developer.
- API menjadi pemilik database dan state sesi. Kontrak deployment awal memakai satu proses API; menambah workers membutuhkan rancangan ownership/synchronization baru.
- Worker tidak membuka atau me-mount database. Lease, heartbeat, lookup konteks, artifact submission, dan result commit melewati internal API dengan scope yang divalidasi server.
- Frontend tidak mengakses database, credential provider, atau private asset path secara langsung.
- Pisahkan raw assets, derivative audio, export, database, scratch, dan backup pada direktori/volume privat.
- Jangan meletakkan audio privat pada bundle frontend atau public static directory.
- Pengujian memakai database/volume disposable; jangan menjalankan reset, migration test, atau destructive fixture pada data developer atau VM bersama.
- Local deployment tetap membutuhkan internet untuk analisis cloud baru. Cached replay tanpa provider harus dibedakan dari inferensi lokal dan instalasi offline.
- Mock profile wajib berlabel `MOCK`; kegagalan provider nyata tidak boleh berubah menjadi fixture yang tampak seperti hasil nyata.

Gunakan manifest dan lockfile yang ada. Baseline repository memiliki `frontend/package-lock.json` dan `pyproject.toml`; jangan mengganti package manager atau mengarang versi pinned tanpa keputusan dan verifikasi kompatibilitas. Python runtime mengikuti batas di `pyproject.toml`, dengan virtual environment untuk pengembangan host.

### 4.4 Data, Clock, dan Bukti

- Setiap import menyimpan provenance, checksum, source kind, hak akses, izin transfer cloud, retention, clock mapping, units, layout version, dan coverage.
- Hak mengunduh dataset tidak otomatis memberikan hak transfer cloud atau redistribusi export. Pengolahan restricted data menunggu izin yang sesuai; pekerjaan dengan sintetik tetap dapat dilanjutkan.
- Pertahankan raw source immutable. Transcript correction, association, review, dan reanalysis menghasilkan revision atau event baru.
- Pisahkan **Said**, **Heard**, dan **Observed**. Matching readback tidak membuktikan gerakan sesuai.
- Pisahkan event time, available time, dan recorded time. Jangan menciptakan available time historis yang tidak tersedia dari sumber.
- As-known replay hanya memakai informasi yang sudah tersedia saat itu; koreksi belakangan masuk debrief dengan label yang jelas.
- Ground truth, private scenario schedule, dan evaluation labels hanya berada pada evaluator boundary; dilarang masuk detector, AI payload, tools, atau observer DTO.
- Critical slots seperti callsign, runway, action, condition, dan negation mempertahankan quote/range dan uncertainty. Jangan menormalisasi dugaan menjadi fakta.
- Identity, timing, geometry, atau coverage yang tidak cukup menghasilkan status seperti `AMBIGUOUS`, `MISSING`, atau `NOT_EVALUABLE`, bukan kesimpulan aman atau runway kosong.
- Accepted findings, options, briefs, dan factual answers wajib memiliki bukti yang resolvable dan sesuai session/run/as-of scope.
- Audio chunk dan derivative mempertahankan time mapping ke audio asli; overlap/dedup serta gaps harus dapat diuji.

### 4.5 AI dan Orkestrasi

- Gemini menangani intent understanding, parsing, bounded context lookup, kandidat association/memory, penjelasan, opsi, serta brief. Backend memegang authority dan accepted state.
- Validasi output dengan Pydantic serta pemeriksaan semantik, entity IDs, quote spans, evidence IDs, scope, dan waktu. JSON yang valid belum tentu benar.
- Tools bersifat read-only, terdaftar, bounded, dan scoped oleh server. Model tidak boleh menentukan permission, session identity, role, atau analysis scope sendiri.
- Batasi tool rounds, timeout, retry, token/usage, dan budget. Simpan failure/refusal/partial status secara eksplisit.
- Transcript dan teks impor adalah data tidak tepercaya. Instruksi yang terkandung di dalamnya tidak boleh mengubah system policy atau tool access.
- Jangan mengaktifkan unrestricted execution, browsing, filesystem access, atau provider tools di luar kontrak v1.
- Accepted result commit harus idempotent. Cancelled jobs, expired leases, stale revisions, dan late results tidak boleh mengubah state secara tidak sah.
- Memori sesi dimiliki aplikasi. Jangan menggantungkan replay pada provider conversation memory yang tidak tercatat.
- Simpan model, API/SDK, prompt/schema, rule/reducer, input revision, dan konfigurasi efektif pada analysis run.
- Jaga auditability tanpa menyimpan chain-of-thought internal; rationale yang ditampilkan berisi penjelasan ringkas dan bukti pendukung.
- Jangan memanggil provider berbayar atau mengirim data nyata hanya untuk memenuhi test tanpa credential, budget, dan hak data yang sesuai dengan tugas.

### 4.6 Frontend, API, dan UX

- Pydantic/OpenAPI menjadi kontrak wire target. Type frontend mengikuti schema server; perubahan kontrak harus memperbarui client, fixture, dan checks terkait.
- Cache key mencakup session, run, revision, dan as-of yang relevan. Jangan menampilkan hasil lintas sesi karena cache key terlalu umum.
- WebSocket memakai urutan event dan snapshot/resync; koneksi kembali tidak boleh menggandakan review atau accepted state.
- Gunakan mutation idempotency dan optimistic version untuk konflik review/config.
- Tampilan membedakan fakta sumber, interpretasi AI, unknown, source alert, dan review manusia.
- Gunakan shadcn/ui dan token terpusat untuk komponen umum; timeline, memory strip, audio player, dan situation view boleh menjadi komponen domain.
- Sertakan loading, empty, unavailable, partial, access denied, stale, serta connection-lost states sesuai alur.
- Severity dan source quality tidak dibedakan hanya dengan warna. Keyboard, focus, label, contrast, overflow, dan audio controls wajib diperiksa pada perubahan terkait.
- Screenshot membantu review visual; assertion state, bukti, authorization, dan interaksi tetap diperlukan.

### 4.7 Secrets, Akses, dan Log

- Credential cloud, session secret, worker secret, data privat, dan raw audio tidak masuk Git, browser, export, screenshot, atau log.
- Sebelum membuat file secret lokal, pastikan path di-ignore, permission terbatas, dan file contoh hanya berisi nama/placeholder.
- Jangan mencetak `.env`, key, authorization header, connection secret, atau signed URL. Jangan menjalankan `source` pada file secret sebagai shortcut konfigurasi.
- Terapkan session/object authorization pada API, WebSocket, media range, export, dan worker tools; filter UI bukan pengamanan akses.
- Proxy menolak internal worker routes dari akses publik. Browser tidak menerima credential internal.
- Default log menggunakan IDs/status/timing/usage; transcript/audio dan provider payload tidak dicatat tanpa kebutuhan serta permission yang jelas.
- Pertahankan batas upload, path sanitization, output escaping, retention, dan revocation. Jangan menonaktifkan kontrol hanya agar demo berhasil.

### 4.8 Deployment, Backup, dan Recovery

- Target services adalah `edge`, `api`, `worker`, dan one-shot `maintenance`. Nama file Compose dan script operasional ditetapkan saat implementasi, bukan dianggap sudah ada.
- VM menyajikan hasil build Vite, bukan Vite dev server. Remote access memakai TLS; API, worker, dan database tidak dipublikasikan langsung.
- Environment terpisah memakai volume, credential, budget, dan config terpisah. Domain, host, branch promotion, serta automation deploy belum dikunci.
- Gunakan image digest/SHA, dependency locks, health checks, resource limits, graceful shutdown, dan release manifest.
- Release memerlukan migration fresh/upgrade, smoke, restart recovery, serta consistent backup/restore checks yang sesuai perubahan.
- SQLite backup harus konsisten ketika WAL aktif. Backup mencakup asset inventory, permissions, retention, dan release/config metadata tanpa secrets plaintext.
- Shared VM membutuhkan backup terenkripsi di luar VM dan restore rehearsal. Restart policy tidak membuktikan high availability.
- Rollback code tidak otomatis membalik migration; jangan restore data tanpa memahami snapshot, kehilangan data setelah snapshot, dan retention/tombstones.
- Tidak ada izin implicit untuk auto-deploy, mengubah DNS, mengganti production data, atau membuka akses operasional.

### 4.9 Cleanup Runtime

- Catat proses, server, watcher, worker, dan container yang dimulai untuk tugas.
- Setelah tidak diperlukan, hentikan hanya runtime yang dimulai untuk tugas tersebut. Jangan menghentikan proses atau stack milik pengguna/sesi lain.
- Jika stack Compose dibuat khusus untuk tugas, gunakan shutdown pada project/config yang tepat. Jangan menjalankan `down -v`, prune global, atau menghapus persistent data sebagai cleanup rutin.
- Jika runtime perlu tetap berjalan untuk inspeksi pengguna, nyatakan URL, alasan, dan cara menghentikannya.
- Periksa kepemilikan runtime sebelum cleanup; jangan menyimpulkan seluruh container pada mesin dibuat oleh agent.

## 5. Verifikasi Lokal dan Release

### 5.1 Memilih Checks

Periksa manifest, scripts, test paths, dan konfigurasi yang tersedia sebelum menjalankan command. Jangan meminjam command CI atau root scripts dari proyek lain.

| Perubahan | Pemeriksaan yang relevan |
| --- | --- |
| Dokumentasi | Konsistensi isi, link/anchor, tabel, code fences, whitespace, dan `git diff --check` |
| Frontend | `npm run typecheck` dan `npm run build` dari `frontend/`; browser/visual checks untuk alur yang berubah setelah harness tersedia |
| Domain/backend | Ruff/mypy sesuai konfigurasi serta pytest unit/contract/numerical yang relevan setelah suites tersedia |
| Data/API/auth | Disposable SQLite integration; schema/client drift, scope, permission, idempotency, concurrency, dan negative tests |
| Clock/replay/geometri | Oracle independen untuk units, footprint, event/available time, gaps, stale tracks, seek, dan reconstruction |
| AI | Provider mocks untuk kontrak/failure; real smoke berizin terpisah; held-out task benchmark untuk kualitas semantik |
| Deployment/database | Compose validation/image smoke, migration fresh/upgrade, restart, backup/restore, dan config checks yang relevan |
| Release/security | Secret/dependency scanning dan security negative cases dengan tooling yang tersedia; hosted jobs jika sudah diprovision |

Baseline scripts frontend yang ditemukan pada 7 Oktober 2026 adalah `dev`, `build`, `typecheck`, dan `preview`. `pyproject.toml` mendeklarasikan pytest dengan `testpaths = ["tests"]`, tetapi suite tidak ditemukan pada inspeksi baseline. Compose, provider pipeline, dan CI belum diprovision dalam baseline. Periksa ulang sebelum memakai inventaris ini sebagai keadaan terbaru.

Gunakan `npm ci` bila setup atau perubahan lockfile memerlukannya. Jangan menginstal ulang dependency atau mengulang seluruh test tanpa perubahan input, failure, atau concern yang relevan.

### 5.2 Kejujuran Evidence dan Failure

- Jalankan checks yang sesuai risiko; perubahan dokumentasi tidak memerlukan build/test aplikasi tanpa alasan khusus.
- Jangan menambah test yang hanya menyalin implementation calculation atau membuat pass tanpa perilaku yang diverifikasi.
- Test geometri/timebase memakai expected value yang ditentukan secara independen.
- Isolasi test data dan fixture; mock/synthetic pass tidak membuktikan provider, fidelity mitra, atau operasi nyata.
- Catat command, cakupan, hasil, dan keterbatasan. Suite yang tidak ada atau test yang tidak dijalankan mendapat status tersebut, bukan PASS.
- Failure yang relevan harus ditangani; jangan menurunkan threshold, menghapus assertion, atau memperluas exception agar check terlihat lulus.
- Jika ada failure yang sudah ada sebelum perubahan, pisahkan bukti baseline dari regression dan jelaskan dampaknya.
- Check yang sudah lulus pada input final tidak perlu diulang untuk checklist kedua. Setelah edit, jalankan ulang hanya checks yang terdampak.

### 5.3 Gate Release

Build lokal atau scoped test pass bukan bukti semua gate release berjalan. Release target mencakup kontrak/type/build, integration, browser, schema/provider, migration, Compose, secret/dependency, dan negative security checks sesuai PRD.

Jika hosted CI sudah tersedia dan push diizinkan, periksa hasil pada candidate SHA yang benar. Failure, cancellation, unexpected skip, dan job yang belum berjalan tidak dilaporkan sebagai keberhasilan.

Real provider smoke memakai data sintetik non-sensitif dengan credential/budget yang sesuai. Benchmarks memisahkan tuning dari held-out test berdasarkan sesi/sumber; report critical-slot errors, wrong pairing, ambiguity/abstention, dan finding eligibility. WER saja tidak membuktikan kualitas produk.

Review domain hanya diberi status selesai jika reviewer nyata dan hasil review tersedia. Research release tanpa review tersebut tetap diberi label `NOT_DOMAIN_VALIDATED`. Jangan mengklaim manfaat keselamatan atau kesiapan operasional dari automated checks.

## 6. Kapan Memperbarui Dokumentasi

Perbarui dokumen yang benar-benar terdampak jika ada perubahan material pada:

- Scope, fitur, interaksi, kewenangan, atau acceptance criteria.
- API, wire schema, enum/status, data model, clock, atau evidence semantics.
- Provider/model, prompt/schema, tool policy, data rights, atau benchmark strategy.
- Storage, migration, worker ownership, deployment, secrets/config, atau recovery.
- Status implementasi yang diperiksa dan hasil verifikasi baru.

Pertahankan PRD sebagai kontrak yang lengkap dan berdiri sendiri. Jangan menambahkan cerita asal template, riwayat percakapan, atau daftar bacaan ke PRD. Dokumentasi teknis khusus menyimpan rincian implementasi tanpa menggandakan seluruh kontrak produk.

Perbarui rencana teknis/addendum yang relevan dan `docs/IMPLEMENTATION_STATUS.md` ketika keputusan target atau evidence implementasi berubah secara berarti. Catat tanggal serta metode pemeriksaan; perubahan dokumentasi saja tidak menaikkan status aplikasi.

### 6.1 Handoff dan Progress

Jika digunakan, `.agent/sessionHandoff.md` memuat objective, changed files, pekerjaan selesai/belum selesai, decisions, blockers, checks, runtime yang ditinggalkan, dan next action. Handoff ringkas tidak menyalin PRD atau seluruh transcript chat.

Jika digunakan, `.agent/implementationPhases.md` memuat urutan pekerjaan, dependencies, acceptance, owner bila diketahui, dan progress. Gunakan `planned`, `in_progress`, `blocked`, `deferred`, atau `done`; status `done` membutuhkan exit evidence. Pertahankan satu fase/subfase utama sebagai current focus. Aktivitas paralel yang memang diizinkan dicatat terpisah dan tidak mengubah dependency menjadi selesai.

Untuk pekerjaan implementasi lintas sesi yang substantif, perbarui handoff bila diperlukan untuk menjaga kesinambungan. Roadmap dan handoff tersedia sejak 7 Oktober 2026; saat dibuat, seluruh fase implementasi masih planned. Jangan mengarang progress atau membuat file tambahan hanya untuk memenuhi ritual pada edit kecil.

## 7. File Baru dan ADR

Tambahkan file hanya ketika ada kebutuhan konteks eksekusi, area operasional, atau keputusan tahan lama yang belum mempunyai tempat yang sesuai.

Nama yang digunakan:

- `.agent/sessionHandoff.md` untuk handoff terkini.
- `.agent/implementationPhases.md` untuk roadmap jika diperlukan.
- `.agent/releaseExecutionChecklist.md` untuk release window jika diperlukan.
- Dokumen stabil lain menggunakan `camelCase.md`.
- ADR menggunakan `docs/adr/000N-kebab-case-title.md` jika directory tersebut digunakan; periksa nomor yang tersedia sebelum membuat file.

ADR diperlukan untuk keputusan arsitektur material seperti perubahan database/ownership, API boundary, provider transport, media processing, deployment, atau recovery. Update ADR yang sama jika memperjelas keputusan yang sudah ada; jangan membuat ADR baru untuk setiap test, edit copy, atau session.

ADR memuat status, tanggal, context, decision, rationale, alternatives, implementation impact, consequences, validation, risks, dan follow-up. Tulis untuk developer/reviewer dengan bahasa profesional. Jangan menyebut prompt pengguna, asal template, percakapan agent, atau nomor fase sebagai alasan arsitektur. Status keputusan dan status implementasi tetap terpisah.

## 8. Git, Commit, dan Delivery

- Periksa branch, diff, dan working tree sebelum edit. Pertahankan perubahan pengguna yang sudah ada dan jangan mengatribusikannya sebagai pekerjaan sesi sendiri.
- Branch default/promotion belum ditetapkan. Jangan membuat aturan `staging` atau mengganti branch tanpa kebutuhan dan otorisasi yang sesuai.
- Jangan melakukan commit, push, merge, deploy, atau publikasi hanya karena task implementasi selesai; lakukan jika instruksi pengguna atau workflow yang diizinkan mencakup tindakan tersebut.
- Hindari destructive Git operations, force push, serta penghapusan uncommitted work tanpa instruksi yang tepat.
- Stage hanya file task yang sesuai; jangan memakai staging global pada working tree yang memiliki perubahan lain.
- Sebelum commit yang diizinkan, pastikan checks relevan pada perubahan final lulus dan secret scan yang sesuai tersedia/dijalankan. Laporkan keterbatasan tooling jika belum diprovision.

Gunakan conventional commit prefixes: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `ci:`, `build:`, dan `chore:`. Subject singkat, spesifik, berbasis perilaku, dan menggunakan bentuk imperatif.

Contoh:

```text
feat: add evidence-backed transcript correction
fix: reject expired worker result leases
docs: define offline replay engineering rules
build: add local Compose runtime
```

Jangan menjadikan nomor fase, posisi roadmap, atau riwayat percakapan sebagai subject commit. Jangan melaporkan delivery berhasil jika hosted checks atau deployment checks yang diwajibkan belum selesai.

## 9. Aturan Konten dan Kolaborasi

- Gunakan Bahasa Indonesia yang mudah dipahami untuk konteks produk; identifier, code, dan istilah teknis dapat tetap dalam English.
- Pisahkan keputusan yang dikunci, pilihan engineering usulan, requirement target, dan evidence implementasi.
- Jangan membuat klaim mitra, hak dataset, SOP lokal, izin regulator, latency, accuracy, atau validasi yang belum terbukti.
- Simulated values, mock UI, dan synthetic fixtures harus diberi label yang sesuai.
- Klaim domain penting mempertahankan scope, tanggal, uncertainty, dan evidence pada dokumentasi riset yang tepat.
- Jangan menyalin batas database, branch, domain, command, CI, atau workflow bisnis dari proyek lain.
- Pertanyaan diajukan bila jawaban memengaruhi scope, data rights, authority, atau keputusan yang benar-benar belum ditentukan. Lanjutkan pekerjaan independen yang sudah diizinkan sambil menunggu.
- Jangan mengulang pertanyaan untuk keputusan yang sudah diberikan. Runtime sizing, penamaan modul, dan pilihan rutin dapat diselesaikan dalam batas kontrak yang berlaku.
- Aturan ini tidak memberi izin membuat/mengirim pesan ke chat lain atau menjalankan agent paralel. Gunakan hanya jika pengguna atau instruksi yang berlaku mengizinkannya.

## 10. Penyelesaian Sesi

Sebelum menyelesaikan pekerjaan:

1. Periksa final diff dan pastikan scope tetap sesuai task.
2. Jalankan checks relevan yang tersedia; catat checks yang tidak dijalankan dan alasannya jika material.
3. Perbarui hanya dokumentasi yang berubah makna atau statusnya; untuk pekerjaan lintas sesi, simpan handoff yang diperlukan.
4. Perbarui roadmap jika status/dependency berubah, dan ADR jika ada keputusan arsitektur material.
5. Cleanup runtime yang dibuat untuk tugas atau jelaskan runtime yang sengaja tetap berjalan.
6. Laporkan hasil, lokasi file penting, verifikasi nyata, serta blocker/limitation yang material secara ringkas.

Edit kecil tidak memerlukan roadmap, handoff, dan ADR baru sekaligus. Pembuatan aturan atau rencana tidak membuktikan aplikasi, integrasi cloud, deployment, atau validasi domain telah selesai.
