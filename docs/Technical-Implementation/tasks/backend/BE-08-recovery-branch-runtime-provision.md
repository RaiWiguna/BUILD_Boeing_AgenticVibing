# BE-08 — Committed-state recovery, branch compatibility, dan runtime provision

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memastikan persistence failure/restart tidak memberi success palsu atau duplicate command effect, dan branching hanya memakai checkpoint compatible.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Session.save mempause sesudah memory mutation saat storage gagal; Archive startup marks interrupted; branch restores private frame tanpa explicit engine/config/schema compatibility check.

**TARGET:** Committed-state recovery/receipts, compatible synthetic branch dan backend dependency/model provisioning manifest untuk offline package. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

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
5. Provision backend dependency lock/runtime manifest sesuai actual chosen stack; ASR/summary optional local assets/models dilaporkan available/unavailable, tanpa unduh/cloud fallback cold-run. Implement konsisten SQLite backup API untuk package/recovery checks.

## 6. Output yang harus diserahkan

Recovery/branch behavior dan versioned runtime/config/dependency manifest untuk QA-06; committed archive tetap dapat direview.

## 7. Asumsi dan unknown

**ASSUMPTION:** Single server writer dan local SQLite; satu RUNNING target utama, bukan benchmark multi-session baru.

**UNKNOWN:** Hardware/model patch/licenses dan volume baseline perlu dicatat dari actual provisioning. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 memiliki failure/branch tests; QA-06 melakukan cold-run package. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Recovery | Command commit fault + same-ID retry | `python -m pytest tests/integration/test_be_08.py` | Tidak ada accepted success sebelum commit; retry menghasilkan paling banyak satu effect. |
| Branch | Compatible/incompatible private checkpoints | Command sama | Parent unchanged, child RNG/queue/response restore; unsupported branch tetap bisa public review. |
| Restart | Interrupted session + committed attempt/revisions | Command sama | No auto-resume/duplicate worker result; durable evidence/history tersedia. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Offline provision | QA-06 package cold-run/network disabled | `python -m pytest tests/integration/test_offline_package.py` | Runtime versi/lock tercatat; missing model degraded tanpa mematikan replay; backup berisi committed records. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
