# BE-01 — Contracts, ports, dan composition boundary

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan DTO replay dan port injection agar session, detector, source, archive reader, dan worker dapat dirangkai tanpa cyclic imports.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** `models.py` mempunyai Pydantic extra-forbid; `Session` mengimpor Simulator/detect/Archive langsung; `create_app` hanya menerima db_path/operator_key/run_clock.

**TARGET:** Tambah kontrak/port dan seam composition sambil mempertahankan synthetic default serta request/stream existing. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/models.py](../../../../backend/models.py)
- [backend/session.py](../../../../backend/session.py)
- [backend/app.py](../../../../backend/app.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §6.2–6.5, §7.2–7.5, §13.1.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/models.py`, `backend/session.py`, `backend/app.py`, `pyproject.toml`

**File baru usulan, belum ada:** `backend/replay_contracts.py`, `backend/ports.py`

BE memiliki DTO transport; SD memiliki DTO detector dan AI DTO assist. Port menggunakan Protocol/typed signature, bukan duplicate domain schema. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Edit `session.py/app.py/models.py` lebih dulu daripada BE-04–08; perubahan config Python berikutnya hanya BE-08.

## 4. Kontrak dan dependency

**Contract:** SC-01/02/03/04/06; C-01/C-02/C-05/C-08 pada indeks. Manifest/ReplayEventRecord dan Reader/Writer/Source/Worker interfaces dikonsumsi BE-02–08; inject detector/lifecycle dengan signature domain, tanpa worker/database imports di DTO.

**Implementation dependency:** Tidak ada output implementasi task lain yang wajib tersedia. Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Inline fake source/detector/lifecycle/worker dan writer yang merekam call order; type-compatible DTO literals ketika domain module belum ada.

**Integration dependency:** BE-02–04, SD-01–05 dan AI-01–02 untuk composition riil.

## 5. Pendekatan implementasi

1. Definisikan schema `replay-1`, source-time/quality sidecars dan version validation C-01; jangan menambah fields ke Track current tanpa adapter.
2. Definisikan ReplayEventSource, ReplayArchiveReader, SessionWriter dan WorkerPort dengan operasi pada SC; DTO tidak mengimpor service.
3. Tambah injection options di constructor/composition root; synthetic default masih menghasilkan payload current dengan kind lowercase, target/runway/revision dan first-message auth.
4. Pisahkan public reader dari private checkpoint capability; worker hanya menerima read-only input dan typed result sink.
5. Dependency config hanya deklarasi yang digunakan kontrak/runtime baseline; jangan memasang provider opsional sebagai syarat import.

## 6. Output yang harus diserahkan

Replay DTO/ports yang dapat diimpor tanpa startup side effects; composition harness menggunakan fake ports untuk seluruh consumer. Existing synthetic callers tetap kompatibel.

## 7. Asumsi dan unknown

**ASSUMPTION:** Kontrak baru additive; schema profile `replay-1` tidak mengganti versi engine current.

**UNKNOWN:** Schema export vendor dan model/hardware tidak diperlukan untuk ports baseline. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki test contract task ini. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Contract | F-REPLAY-01 manifest/record | `python -m pytest tests/contracts/test_be_01.py` | Round-trip mempertahankan source ID, time/unit dan quality; unknown profile ditolak. |
| Negative | Extra field, nonfinite timestamp, private checkpoint request | Command sama | Payload invalid ditolak; public reader tidak mengeluarkan private state. |
| Compatibility | Fake ports + current CreateSession/Command | Command sama | Synthetic default memakai wire existing; importing DTO tidak membuat DB/worker. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Composition | BE+SD+AI stub profile | `python -m pytest tests/integration/test_composition.py` | Orchestrator satu writer; domain/provider tidak mengimpor Session/Archive. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
