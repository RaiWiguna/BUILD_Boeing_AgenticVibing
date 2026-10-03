# SD-05 — Alert lifecycle dan experimental task complexity

**Owner-role:** Simulation/Detection

**Packet induk:** [simulation-detection.md](../../packages/simulation-detection.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menyediakan pure lifecycle policy dan complexity function yang dapat dipersist BE tanpa ack/dropout false-resolution.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Session.evaluate mengelola severity/lifecycle timer; task_complexity di detection.py memakai role traffic/channel union/pending tasks/config, tidak alert severity.

**TARGET:** Pure lifecycle extraction dan complexity formula boundary verification. Tidak mengedit Session/Archive/API, menjalankan ASR, atau mengambil keputusan operasi.

## 3. Context dan ownership

- [backend/session.py](../../../../backend/session.py)
- [backend/detection.py](../../../../backend/detection.py)
- [backend/models.py](../../../../backend/models.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §10.3–10.5, §11, §16.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/detection.py`

**File baru usulan, belum ada:** `backend/alert_lifecycle.py`

SD membuat policy baru, BE-01/08 saja mengedit Session glue; transition payload belum mempunyai server event ID sampai BE assigns. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. detection.py sesudah SD-04 untuk complexity; tidak mengedit session.py.

## 4. Kontrak dan dependency

**Contract:** SC-01/03. Previous alerts+DetectionResult+now_ms→alerts/transitions; role observations/channel spans→complexity score/components/weights/model_version. Consumer BE/FE.

**Implementation dependency:** [SD-04](../simulation-detection/SD-04-deterministic-rules-quality-evidence.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Prior ACTIVE/RESOLVED incidents+fixed candidate sets; F-QUALITY-01 and channel span oracle tanpa Archive.

**Integration dependency:** BE-02/08 session composition dan BE-03 archived transitions.

## 5. Pendekatan implementasi

1. Extract lifecycle policy tanpa DB/Session imports; dedup rule/physical runway/sorted objects dalam session namespace.
2. Escalate immediately; downgrade/resolution hanya setelah tiga detik sim dengan adequate observations; pause tidak menjalankan age/timer.
3. Acknowledgement separate, stale active threat menahan safe timer; reappearing resolved hazard membuka incident baru dengan ancestry.
4. Pertahankan experimental complexity formula dan role-scoped traffic/union channel duration, no double-count overlaps; report components/weights/model_version.
5. Typed numeric failure/invalid candidate return quality/error untuk orchestrator; tidak menyatakan safe atau mengubah recorded truth.

## 6. Output yang harus diserahkan

AlertLifecyclePort implementation dan role complexity outputs untuk BE persistence/FE display; evidence version/transition causal references utuh.

## 7. Asumsi dan unknown

**ASSUMPTION:** Tiga detik sim dan complexity weights adalah baseline eksperimen kanonis.

**UNKNOWN:** Human workload/fatigue validity dan site calibration belum tersedia. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-02 memiliki lifecycle/complexity independent formula tests. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Lifecycle | Ack/escalation/downgrade/resolve/reappear | `python -m pytest tests/unit/test_sd_05.py` | Ack tidak resolve; severity naik segera, turun/resolve sesudah stable 3 s yang memadai. |
| Negative | Dropout active threat, paused clock | Command sama | Threat tetap active/degraded; safe timer tidak age karena wall time. |
| Complexity | Overlapping channel spans+role ownership | Command sama | Duration union benar, formula independent match, no alert-severity term. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Archived lifecycle | BE session/archive+FE evidence | `python -m pytest tests/integration/test_alert_archive.py` | Transitions disimpan sekali per incident change; replay alerts/ack/complexity sama dengan recorded frame. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
