# BE-03 — Import replay atomik dan archive immutable

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menerima normalized offline export dan menyimpan manifest/source records serta derived frame versions secara atomik dan dapat dibaca ulang.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Archive mempunyai tabel sessions/events/frames/commands; frames current replace pada session_id+sim_ms, tanpa source/import/analysis schema version table.

**TARGET:** Import validator/staging dan archive extensions versioned untuk replay source/analysis tanpa mengganti history synthetic. Tidak mencakup geometri/rule body, inferensi provider, UI, atau source live.

## 3. Context dan ownership

- [backend/storage.py](../../../../backend/storage.py)
- [backend/models.py](../../../../backend/models.py)
- [backend/scenarios.py](../../../../backend/scenarios.py)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §7.1–7.3, §7.8, §14.1–14.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** `backend/storage.py`

**File baru usulan, belum ada:** `backend/replay_import.py`

Source bytes/hash immutable; analysis data terpisah. Schema persistence di storage BE, tests temp DB oleh QA. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. Pemilik edit storage.py: BE-03 lalu BE-08. BE-05–07 memakai assist_storage.py terpisah.

## 4. Kontrak dan dependency

**Contract:** SC-01/02/06. Manifest+events.jsonl C-01→{source_session_id,source_id,import_status}; frame query C-02. Consumer BE-04 dan assist evidence queries.

**Implementation dependency:** [BE-01](../backend/BE-01-contracts-ports-composition.md), [BE-02](../backend/BE-02-replay-source-state-reducer.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Canonical authored bundle atau inline JSONL, InMemoryWriter failure injection; detector stub untuk frame analysis.

**Integration dependency:** BE-02 reducer dan BE-04 HTTP import/read service.

## 5. Pendekatan implementasi

1. Implementasikan import parser manifest+JSONL C-01, hash exact event bytes, finite/unit/time/geometry/identity validation; unsupported vendor format menjadi explicit unsupported.
2. Stage private input dan validate seluruh records sebelum visibility; identical IDs dedup, changed payload conflict; authorized label memerlukan provenance penggunaan yang tercatat.
3. Tambahkan versioned persistence extensions dengan transaksi SQLite; existing schema dibaca tanpa rename/drop data. Imported frames berkey source+analysis+frame time agar re-analysis tidak menimpa historical output.
4. Commit manifest+source events bersama, lalu publish completed receipt. Kegagalan meninggalkan sumber lama utuh; partial analysis boleh unavailable tanpa memalsukan successful predictions.
5. Query records menggunakan until_ms sebelum pagination dan pisahkan reader public/private; import retry same source/hash mengembalikan existing source, different hash menjadi conflict.

## 6. Output yang harus diserahkan

Immutable import/archive service, schema-version compatibility reader, dan public frame/event APIs internal untuk BE-04; perubahan schema tetap target implementasi.

## 7. Asumsi dan unknown

**ASSUMPTION:** File export baseline terdiri dari manifest JSON dan event JSONL; tanpa vendor connector.

**UNKNOWN:** Volume/retensi dan versi export mitra. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 memiliki temporary SQLite import suite. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Persistence | F-REPLAY-01 di temp DB | `python -m pytest tests/integration/test_be_03.py` | Reopen mempertahankan manifest/hash/events/frame versions. |
| Negative | Commit failure, invalid final row, conflicting source ID | Command sama | Tidak ada half-import visible; source lama tidak berubah. |
| Compatibility | DB schema current + same-time frames | Command sama | Existing archive tetap readable; analysis baru tidak replace historical namespace. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Import/read HTTP | BE-04 + parser/reducer riil | `python -m pytest tests/integration/test_replay_import_api.py` | Receipt completed hanya setelah commit; repeated import sama tidak membuat dua source. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
