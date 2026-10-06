# BE-03 — Import replay atomik dan archive immutable

**Owner-role:** Backend/Replay

**Packet induk:** [backend-session-replay-storage.md](../../packages/backend-session-replay-storage.md)
**Status per 4 Oktober 2026:** source BE-03 tersedia; suite SQLite sementara lulus, 10 tests. Belum ada route HTTP BE-04, integrasi mitra, review domain, atau validasi operasional.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Menerima normalized offline export dan menyimpan manifest/source records serta derived frame versions secara atomik dan dapat dibaca ulang.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Synthetic Archive tetap memakai tabel sessions/events/frames/commands; frame synthetic tetap replace pada `(session_id, sim_ms)`.

**IMPLEMENTED_SOURCE:** `backend/replay_import.py` memvalidasi normalized `replay-1`, menghitung hash dari bytes JSONL persis, mendeduplikasi identity yang payload-nya identik, dan memanggil transaksi import atomik. `backend/storage.py` menambah tabel schema marker, source/session metadata, source records, completed receipts, analysis versions, dan analysis frames dengan namespace serta aturan append-only terpisah. Internal event-source dan public projection reader tersedia.

**BATAS:** Tidak mencakup geometri/rule body, inferensi provider, UI, route HTTP, atau source live. Import source synthetic fixture tidak memverifikasi permission atau fidelity operasi.

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

1. Parser menolak schema/vendor mentah yang belum normalized, malformed JSON, hash mismatch, identitas berbeda, unit/clock/timebase yang bertentangan, waktu nonfinite/tidak dapat dipetakan, dan geometry/layout yang tidak sesuai DTO.
2. Semua record divalidasi sebelum transaksi. Identity event sama dengan payload berbeda menjadi conflict; duplikat identik didedup. Timestamp/alignment yang unknown tetap unknown dan tidak diberi nilai nol.
3. SQLite menambahkan schema replay version 1 dan tabel source/session/records/receipt serta analysis/frame; tabel synthetic tidak diubah. Source, records, receipt, analysis, dan frames append-only.
4. Manifest canonical, original event bytes/hash, source metadata, records, dan completed receipt ditulis dalam satu transaksi. Source ID yang sama retry idempotent hanya jika hash, bytes, dan metadata canonical sama.
5. Public reader memilih frame terakhir `<= at_ms`, menerapkan `until_ms` di query sebelum limit, dan hanya mengembalikan projection; event source internal tetap baca-saja dan mempertahankan record unresolved.

## 6. Output yang harus diserahkan

`ReplayImportService`, schema SQLite replay aditif dengan reader yang tetap dapat membuka archive synthetic lama, immutable import/archive persistence, `ArchiveReplayEventSource`, dan `SQLiteReplayArchiveReader` untuk consumer internal BE-04. Tidak ada route transport.

## 7. Asumsi dan unknown

**ASSUMPTION:** File export baseline terdiri dari manifest JSON dan event JSONL; tanpa vendor connector.

**UNKNOWN:** Volume/retensi dan versi export mitra. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

`tests/integration/test_be_03.py` memakai fixture sintetik inline dan temporary SQLite. Hasil yang dijalankan pada 4 Oktober 2026 dicatat di §9.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Persistence | Synthetic bundle di temporary SQLite | `python -m pytest tests/integration/test_be_03.py` | Lulus: reopen mempertahankan manifest, hash bytes, source records, receipts, dan frame analysis. |
| Negative | Hash mismatch, source/hash/manifest conflict, duplicate conflict, invalid record terakhir, injected pre-commit failure | Command sama | Lulus: tidak ada partial source/receipt dan committed source lama tetap utuh. |
| Compatibility | Synthetic archive current + imported same-time analysis versions | Command sama | Lulus: frame/metadata synthetic tetap terbaca; source analysis terpisah dan tidak menimpa versi lain. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Import/read HTTP | BE-04 + parser/reducer riil | `python -m pytest tests/integration/test_replay_import_api.py` | Receipt completed hanya setelah commit; repeated import sama tidak membuat dua source. |

HTTP check pada BE-04 tetap target, karena route dan API transport di luar ownership BE-03.

## 9. Verifikasi dan batas hasil

- `python -m pytest tests/integration/test_be_03.py` — lulus, 10 tests. Fixture authored/sintetik dan temporary SQLite; termasuk reopen, byte-exact hash, retry/conflict, duplicate identity, invalid tail, injected pre-commit rollback, compatibility synthetic, same-time analysis versions, cutoff/page, public projection, dan unknown-time unresolved preservation.
- `python -m ruff check backend/storage.py backend/replay_import.py tests/integration/test_be_03.py` — lulus.
- `python -m mypy --follow-imports=skip backend/storage.py backend/replay_import.py tests/integration/test_be_03.py` — lulus untuk tiga file; imported modules dilewati.
- `git diff --check` — exit 0; Git memberi pemberitahuan line-ending pada `backend/storage.py`.
- Test membuktikan service berjalan di test harness menggunakan SQLite sementara saja. Tidak ada build/deployment, API BE-04, data/adapter mitra, review pakar domain, atau validasi operasional yang dijalankan.
