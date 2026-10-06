# BE-02 — Replay source reader dan observed-state reducer

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** Source BE-02 tersedia; stub verification lulus pada 4 Oktober 2026. Belum ada integrasi source/SD mitra atau validasi domain/operasional.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Membangun observed state pada receive time replay dengan urutan stabil dan tanpa menyuntikkan initial synthetic objects ke imported source.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** `Session.__init__` membuat Simulator dan initial clearances; `advance` menimpa track delivered tanpa per-source out-of-order guard.

**IMPLEMENTED_SOURCE:** `backend/replay_source.py` menyediakan reader dedup/conflict-aware, reducer state observed yang dibangun ulang per cutoff, dan analysis frames in-memory melalui detector/lifecycle injection. Modul ini tidak memakai constructor `Session` atau `Simulator`, tidak membaca roster private, dan tidak menulis persistence.

**BELUM TERINTEGRASI:** Base `DetectorPort` BE-01 belum menerima layout source. Modul menambahkan structural extension opsional `evaluate_with_layout`; tanpa extension itu frame mencatat `not_exposed_by_detector_port` dan analysis berstatus degraded. Detector source `backend/detection.py` saat ini memakai geometri global sintetik, sehingga fidelity geometri imported layout belum diverifikasi.

## 3. Context dan ownership

- [backend/session.py](../../../../backend/session.py)
- [backend/models.py](../../../../backend/models.py)
- [backend/simulator.py](../../../../backend/simulator.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.5–7.8, §8.2, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru yang dibuat:** `backend/replay_source.py`, `tests/unit/test_be_02.py`, dan `tests/integration/test_replay_analysis.py`.

BE mengelola state/ordering; SD hanya menghitung result/lifecycle. Tidak membaca future simulator schedule. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Tidak berbagi file implementasi dengan task lain yang perlu urutan edit.

## 4. Kontrak dan dependency

**Contract:** SC-01/02/06. ReplayEventRecord→observed/current/previous tracks, clearances, requests, runway/coverage→SC-03 detector input. Public read state memakai C-02; analysis identities C-05.

**Implementation dependency:** [BE-01](../backend/BE-01-contracts-ports-composition.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** InMemoryEventSource dan StubDetector/Lifecycle; roster public coverage tanpa private mobiles.

**Integration dependency:** BE-03 archive dan SD-02–05 untuk derived frames.

## 5. Pendekatan implementasi

1. Pisahkan `apply_source_event` dan `build_state(at_ms)` dari constructor synthetic; consume event sampai normalized receive time lalu ordinal.
2. Dedup berdasarkan source identity; simpan late packet tetapi jangan memundurkan latest sample per source/object. Same-time ties gunakan ordinal.
3. Map structured CLEARANCE/CANCEL/READBACK/COORDINATION/config inputs; COMMAND audit tidak dieksekusi ulang bersama resulting event.
4. Records missing/unmapped timestamp tetap unresolved input; state mempunyai missing coverage, tidak mengisi observed time atau posisi nol.
5. Jalankan detector/lifecycle via injected ports pada time budget tersedia dan hasilkan frames dalam namespace analysis tersendiri; jangan overwrite native source alerts.

## 6. Output yang harus diserahkan

Reducer/source reader dan builder analysis frames untuk BE-03/04, SD integration, serta public EvidenceReader input AI.

## 7. Asumsi dan unknown

**ASSUMPTION:** Clock fixture memakai offset konstan dengan uncertainty yang dicatat; source log append-only.

**UNKNOWN:** Vendor identity mapping, event types dan drift nonlinear belum diketahui. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki unit reducer; QA-03 menguji integration persistence. Verifikasi BE-02 yang dijalankan memakai inline synthetic fixtures dan stubs; belum membuktikan persistence BE-03 atau detector/provider riil.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Unit | Same-time clearances/tracks, duplicate, late sample, unresolved, cutoff, COMMAND/native alert, causality | `python -m pytest tests/unit/test_be_02.py` | Lulus, 8 tests pada 4 Oktober 2026. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Source/detector stubs | Inline synthetic source, injected detector/lifecycle, source hash/evidence/privacy | `python -m pytest tests/integration/test_replay_analysis.py` | Lulus, 1 test pada 4 Oktober 2026; in-memory only, tanpa database/socket. |

Task menghasilkan output source §6 dan assertions stub yang ditentukan telah lulus. Ini tidak membuktikan build aplikasi, runtime deployment, integration persistence, domain review, fidelity mitra, atau validasi operasional.

## 9. Verifikasi dan batas hasil

- `python -m pytest tests/unit/test_be_02.py` — lulus, 8 tests.
- `python -m pytest tests/integration/test_replay_analysis.py` — lulus, 1 test; pipeline source reader → reducer → detector/lifecycle stub dieksekusi dalam test harness.
- `python -m ruff check backend/replay_source.py tests/unit/test_be_02.py tests/integration/test_replay_analysis.py` — lulus.
- `python -m mypy --follow-imports=skip backend/replay_source.py` — lulus untuk file reducer; imported modules dilewati.
- `git diff --check` — exit 0. Git menampilkan pemberitahuan line-ending pada file BE-01/pengguna yang sudah berubah di working tree.
- Tidak ada build atau server terpisah yang dijalankan. Belum ada source simulator mitra, adapter import, persistence/API BE-03, detector SD dengan geometri source, review pakar domain, atau validasi operasional.
