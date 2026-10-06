# BE-08 — Committed-state recovery, branch compatibility, dan runtime provision

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** SOURCE IMPLEMENTED; scoped verification lulus 5 Oktober 2026. Bukan bukti cold-run package atau validasi operasional.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memastikan persistence failure/restart tidak memberi success palsu atau duplicate command effect, dan branching hanya memakai checkpoint compatible.

## 2. Kondisi saat ini dan batas pekerjaan

**SOURCE SEBELUM BE-08:** Session.save mempause sesudah memory mutation saat storage gagal; Archive startup marks interrupted; branch restores private frame tanpa explicit engine/config/schema compatibility check.

**SOURCE SETELAH BE-08:** Session memulihkan memory/cursor ke committed snapshot saat writer gagal, memeriksa receipt/frame untuk hasil commit ambigu, dan memberi diagnostic aman/paused state. Checkpoint synthetic memiliki schema/engine/config/scenario/layout metadata; kompatibilitas diperiksa sebelum child dibuat. Branch memakai row/frame/event ancestry dalam commit pertama yang lengkap. Archive menyediakan SQLite backup API dan route manifest runtime berversi.

**BATAS:** Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live. Tidak dibuat pinned lock; `pyproject.toml` tetap mendeklarasikan dependency ranges. Manifest mencatat versi distribution yang benar-benar terpasang, environment/config runtime, dan ketersediaan worker/model tanpa mengklaim cold-run.

## 3. Context dan ownership

- [backend/session.py](../../../../backend/session.py)
- [backend/storage.py](../../../../backend/storage.py)
- [backend/review.py](../../../../backend/review.py)
- [backend/app.py](../../../../backend/app.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §13.4–13.7, §14.3–14.4, §16.2 dan §18.7.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/session.py`, `backend/storage.py`, `backend/review.py`, `backend/app.py`, `backend/__init__.py`, `pyproject.toml`

**File baru usulan, belum ada:** Tidak ada file source baru di task ini.

SD owns RNG/checkpoint mechanics; BE owns commit/recovery/version checks. QA-06 owns package script; no live deployment. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Task ini terakhir mengedit shared BE files sesudah BE-07; storage.py sesudah BE-03.

## 4. Kontrak dan dependency

**Contract:** SC-02/03/04/06 dan C-05/C-08. SC-02 writer/receipt and SC-03 state restore; C-05/08 versions/receipts. Runtime source/analysis readers tetap kompatibel saat branch disabled.

**Implementation dependency:** [BE-03](../backend/BE-03-atomic-replay-import-archive.md), [BE-07](../backend/BE-07-append-only-review-debrief.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Fault-injection writer, private checkpoint fixture with incompatible versions, process restart temp DB, provider unavailable stub.

**Integration dependency:** SD-02 checkpoint restore, BE-05/06 attempts/revisions dan QA-06 offline packaging.

## 5. Pendekatan implementasi

1. Snapshot pre-mutation committed state atau stage proposed command state; publish command success hanya setelah atomic commit. Failure restores last committed memory/cursor lalu paused/diagnostic.
2. Retry command_id mengambil durable receipt; rejected/failed command tidak menggandakan event/revision. Unknown post-failure outcome diperiksa receipt, bukan reapply.
3. Startup interrupted source tidak auto-resume; recover job attempts dengan explicit state, tanpa inference otomatis dari job yang hasilnya mungkin sudah committed.
4. Check schema/engine/config/layout/checkpoint compatibility sebelum branch. Restore RNG/queued observations/pending responses dan parent evidence ancestry; imported source tanpa checkpoint menolak branch tetapi tetap review.
5. Sajikan runtime/config/dependency manifest berdasarkan `pyproject.toml` dan environment berjalan; worker port dan local model diberi status available/unavailable, tanpa membuka secret/path privat. SQLite backup memakai `Connection.backup()` dan tujuan hanya dipilih caller tepercaya di luar request publik.

## 6. Output yang harus diserahkan

Recovery/branch behavior, versioned runtime/config/dependency manifest untuk QA-06, SQLite snapshot backup, serta committed archive yang tetap dapat direview.

## 7. Asumsi dan unknown

**ASSUMPTION:** Single server writer dan local SQLite; satu RUNNING target utama, bukan benchmark multi-session baru.

**UNKNOWN:** Hardware/model patch/licenses dan volume baseline perlu dicatat dari actual provisioning. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 menjalankan failure/branch tests BE-08 dengan TestClient, temporary SQLite, fake clock, fault-injection writer, dan synthetic fixtures. QA-06 cold-run package tetap target dan belum dijalankan.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Recovery | Pre-commit dan post-commit injected writer failures, command retry/collision/stale revision, acknowledgement/assessment/tick rollback | `python -m pytest tests/integration/test_be_08.py` | Lulus: 6 BE-08 tests; tidak ada success sebelum commit terkonfirmasi atau duplicate command effect. |
| Branch | Compatible checkpoint dan ancestry; missing checkpoint schema; imported replay review/branch boundary | Command sama | Lulus: parent tetap sama, simulator private state/ancestry dipulihkan; child incompatible tidak terlihat; imported review tetap terbaca. |
| Restart/backup/manifest | Interrupted session, BE-07 corrections/annotations/receipts/sequence/debrief, SQLite online backup, runtime manifest | Command sama | Lulus pada temporary SQLite dan synthetic fixtures; tidak memulai worker setelah reopen. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Offline provision | QA-06 package cold-run/network disabled | `python -m pytest tests/integration/test_offline_package.py` | Runtime versi/lock tercatat; missing model degraded tanpa mematikan replay; backup berisi committed records. |

Verifikasi 5 Oktober 2026:

- `python -m pytest tests/integration/test_be_03.py tests/integration/test_be_04.py tests/integration/test_be_05.py tests/integration/test_be_06.py tests/integration/test_be_07.py tests/integration/test_be_08.py` — lulus, 58 tests.
- `python -m ruff check --ignore B008,UP041 backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` — lulus.
- `python -m mypy --follow-imports=skip backend/app.py backend/session.py backend/storage.py backend/review.py backend/__init__.py tests/integration/test_be_08.py` — lulus; imported modules dilewati sesuai opsi.
- `git diff --check` — exit 0; Git menampilkan peringatan line-ending LF→CRLF untuk file backend yang berubah.

Offline package cold-run/network-disabled, build, deployment, provider inference, domain review, replay mitra berizin, dan validasi operasional tidak dijalankan. Hasil test adalah bukti TestClient/SQLite sementara dengan data dan worker sintetik.
