# BE-02 — Replay source reader dan observed-state reducer

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Membangun observed state pada receive time replay dengan urutan stabil dan tanpa menyuntikkan initial synthetic objects ke imported source.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** `Session.__init__` membuat Simulator dan initial clearances; `advance` menimpa track delivered tanpa per-source out-of-order guard.

**TARGET:** Pure reducer, cursor source reader, dan orchestration analisis detector pada sumber yang telah dinormalisasi. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/session.py](../../../../backend/session.py)
- [backend/models.py](../../../../backend/models.py)
- [backend/simulator.py](../../../../backend/simulator.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.5–7.8, §8.2, §14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `backend/replay_source.py`

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

QA-02 memiliki unit reducer; QA-03 menguji integration persistence. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Unit | Same-time clearances/tracks | `python -m pytest tests/unit/test_be_02.py` | State sama untuk record order yang dinormalisasi; ordinal menentukan ties. |
| Negative | Late sample, missing time, duplicate/conflicting IDs | Command sama | Late packet tidak menimpa track baru; unresolved input tidak menghasilkan fresh state. |
| Boundary | Imported source tanpa BAW123/ARFF-2 | Command sama | Tidak ada phantom mobiles/clearances dan future event di at_ms lebih awal. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Archive/detector | F-REPLAY-01 dan F-QUALITY-01 | `python -m pytest tests/integration/test_replay_analysis.py` | Frames/evidence menunjuk committed source dan analysis version, source hash tetap. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
