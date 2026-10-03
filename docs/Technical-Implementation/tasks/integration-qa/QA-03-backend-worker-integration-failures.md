# QA-03 — Backend, detector, dan worker integration failures

**Owner-role:** Integration/QA

**Packet induk:** [integration-qa.md](../../packages/integration-qa.md)
**Status:** TARGET / belum diimplementasikan sebagai deliverable task. Inspeksi statis: 4 Oktober 2026.

[Indeks task](../README.md) · [Shared contracts](../../shared-contracts.md). Penyempurnaan C-01–C-08 dan aturan ownership/test pada indeks berlaku; ini dokumentasi, bukan hasil runtime.

## 1. Target

Memverifikasi atomic import, scopes, replay/source immutability, detector/worker integration dan recovery melalui temp SQLite/FastAPI/WS.

## 2. Kondisi saat ini dan batas pekerjaan

**CURRENT_SOURCE:** Source has create_app(db_path,operator_key,run_clock) seam, Archive and Review but no integration tests; assist runtime absent.

**TARGET:** All BE/SD/AI integration paths/fixtures, historical/source isolation, attempt/review recovery; stubs for external providers. Tidak mengubah feature source milik workstream lain atau mengklaim domain/operational validation.

## 3. Context dan ownership

- [backend/app.py](../../../../backend/app.py)
- [backend/storage.py](../../../../backend/storage.py)
- [backend/session.py](../../../../backend/session.py)
- [backend/review.py](../../../../backend/review.py)
- [backend/reporting.py](../../../../backend/reporting.py)
- [pyproject.toml](../../../../pyproject.toml)
- [Rencana Teknis MVP](../../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md), §13–14, §16.2.
- [AI Assist Buddy](../../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), §1 dan §3–5 bila terkait.

**Existing yang dimiliki task:** Tidak ada perubahan file existing.

**File baru usulan, belum ada:** `tests/integration/`

QA-03 owns every integration test named in producer §8 except offline_package/performance files explicitly QA-06; no production source edits. Tests/fixtures executable tetap milik QA; task ini menentukan perilaku yang harus diuji. tests/integration files disjoint from QA-06 reservation; test modules added per available implementation, not gate others.

## 4. Kontrak dan dependency

**Contract:** SC-01–07. Public source+temp DB+typed result+scoped identities→actual API/WS/persistence assertions; consumers BE/SD/AI/FE confidence in adapter integration.

**Implementation dependency:** [QA-01](../integration-qa/QA-01-canonical-fixtures-independent-oracles.md), [QA-02](../integration-qa/QA-02-contract-unit-test-suites.md) Dependency lintas workstream dapat memakai stub; output runtime riil hanya diperlukan saat integrasi.

**Mock/stub:** Stub detector/lifecycle/worker plus explicit operator test key injected; temporary storage, fake wall clock; no real runtime credentials.

**Integration dependency:** BE-01–08, SD-01–05, AI-01–05; providers may stub. Real ASR eval optional corpus path test_asr_provider.

## 5. Pendekatan implementasi

1. Buat harness create_app/temp DB terisolasi dengan run_clock=False untuk deterministic seek; harness clock aktif hanya untuk menguji isolasi worker.
2. Implementasikan suites backend per producer serta replay_analysis/import_api/prediction_archive/rule_lifecycle/alert_archive; terapkan until_ms sebelum limit pagination.
3. Uji auth/token expiry, source-read versus review-control, baseline/observer/private truth/future transcript/evidence secara negatif.
4. Inject commit fault/restart/duplicate commands dan worker timeout/cancel/late invalid results; periksa jumlah data persisten serta hash source.
5. Uji raw→correction→reopen dan checkpoint branch berpasangan; external source alerts tetap asalnya. Evaluasi ASR riil mengukur metrics tanpa threshold kualitas buatan.

## 6. Output yang harus diserahkan

Integration suites dan hasil pemeriksaan persisted evidence/compatibility yang tepat untuk seluruh paket server.

## 7. Asumsi dan unknown

**ASSUMPTION:** SQLite lokal sementara serta provider stub memungkinkan pengujian tanpa data mitra atau asset model.

**UNKNOWN:** Hasil runtime server/provider belum diukur; tests in-process tidak membuktikan LAN multi-mesin. Pengembangan baseline memakai fixture/stub; tidak memalsukan fakta mitra atau hasil pengukuran.

## 8. Test dan kriteria lulus

QA-03 tests mandiri menggunakan backend riil ketika tersedia dan stub domain/provider; actual merged component checks terpisah. Seluruh command berikut adalah TARGET setelah test/runner dibuat; tidak dijalankan dalam penyusunan dokumentasi ini.

Tests mandiri (dependency luar memakai stub):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| API/persistence | All F-* and temp SQLite | `python -m pytest tests/integration -k 'not offline_package and not performance and not asr_provider'` | Commit before success, scope/private boundaries, stable source/hash/versions and current wire compatibility. |
| Negative/fault | Disk error/cross-source/stale revision/late result | Command sama | No duplicate effect/false saved state; source review still readable where storage usable. |
| Compatibility | Historical current schema and checkpoints | Command sama | Archived review readable; incompatible branch rejected explicitly. |

Integration checks (memerlukan implementation riil yang disebut pada §4):

| Test/check | Input/fixture | Cara menjalankan | Hasil yang wajib diperoleh |
|---|---|---|---|
| Real detector/worker | SD implementation+AI worker queue replacing fakes | `python -m pytest tests/integration/test_composition.py tests/integration/test_worker_lifecycle.py tests/integration/test_replay_analysis.py` | One writer, same domain contract, source/clock unaffected by ASR failure. |
| ASR riil | Provisioned local model+private labels corpus | `python -m pytest tests/integration/test_asr_provider.py` | Measured per-profile WER/slots/attribution/alignment; unavailable assets clearly reported, no invented pass metric. |

Task memenuhi kriteria teknis ketika output §6 tersedia dan assertions relevan di atas lulus dengan bukti command/fixture/version. Stub pass dilaporkan terpisah dari integration/provider riil; tidak menyatakan fidelity mitra atau validasi operasional.
