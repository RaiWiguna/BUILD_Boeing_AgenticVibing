# QA — Integration/QA dan offline packaging

**Owner-role:** Integration/QA. **Status:** `TARGET/PROPOSED_CONTRACT`, inspeksi 3 Oktober 2026. [Master](../README.md) · [Shared contracts](../shared-contracts.md).

## Objective dan output

Memeriksa kesamaan kontrak lintas workstream sejak awal dengan fixture/stubs, lalu memverifikasi replay end-to-end ketika runtime tersedia. Output implementasi: canonical public/private fixture bundle, independent numerical/label oracles, port/transport contract tests, integrated failure/reconnect/review checks, browser scripts, mock-stack launcher dan paket offline synthetic.

Consumer semua paket dapat memakai fixture/test expectations tanpa menunggu full runtime. QA tidak memproduksi ground truth dari output model/detector yang sedang dinilai, tidak menetapkan sign-off/approval, dan tidak menyebut keberhasilan teknis sebagai domain/operational validation.

## CURRENT/TARGET dan scope

| Label | Kondisi |
|---|---|
| CURRENT_SOURCE | `pyproject.toml` memiliki optional pytest/httpx/Playwright/ruff/mypy dan testpaths `tests`; direktori tests tidak ditemukan |
| CURRENT_SOURCE | FE punya scripts typecheck/build/dev; App/styles dan dist/index.html belum tersedia; scripts existing adalah alat presentasi, bukan launcher aplikasi |
| TARGET | Contract tests/fixtures early, mock stack, numerical/API/browser integration, recovery/privacy/outage isolation, offline package manifest |
| UNKNOWN | Provider assets/runtime installability, benchmark hardware/LAN, vendor replay dan domain-reviewed corpus; hasil checks aplikasi belum ada |

Included: mechanical contract, determinism/evidence/time isolation, numerical geometry, API scope/revisions, ASR stubs/failure fixtures, frontend mock/integrated browser, offline packaging boundary. Excluded: feature implementation milik BE/SD/AI/FE, live feeds/audio, real data tanpa izin, human study sebagai automated test, approval workflow, deployment internet dan fabricated accuracy/performance targets.

## Context packet

- [Shared contracts](../shared-contracts.md) SC-01–07 dan [master ownership/dependencies](../README.md).
- [BE](backend-session-replay-storage.md), [SD](simulation-detection.md), [AI](ai-harness.md), [FE](frontend-replay-review.md) sebagai daftar outputs/verification yang harus dihubungkan.
- [pyproject.toml](../../../pyproject.toml), [package.json](../../../frontend/package.json), [vite.config.ts](../../../frontend/vite.config.ts), [main.tsx](../../../frontend/src/main.tsx) untuk commands/config current; belum diuji.
- [app.py](../../../backend/app.py), [storage.py](../../../backend/storage.py), [review.py](../../../backend/review.py), [session.py](../../../backend/session.py) untuk runtime/source/receipt/seek checks.
- [Plan](../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md) §15–16 dan §14: fixture/oracle/replay/acceptance/performance; [AI addendum](../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md) §5 untuk paired evidence/evaluation minimum.

Context source SD/AI/FE dimuat ketika check terkait tersedia, bukan seluruh repository. Tidak ada automated test yang ditemukan untuk dijadikan hasil lulus sebelumnya.

## Modul/file ownership

QA memiliki path baru usulan, semuanya belum ada:

```text
tests/
  fixtures/replay/       # public manifest/events/frames/geometry
  fixtures/assist/       # assets metadata, synthetic audio/stub segments/options
  fixtures/private/     # evaluator labels/oracles; tidak ikut public serializer
  contracts/            # source/detector/worker/API/UI parity
  unit/                 # pure-clock/geometry/rules/reconcile/adapter checks
  integration/          # SQLite/FastAPI/WS/worker round-trip dan failures
  browser/              # native Python Playwright
scripts/run_mock_stack.py
scripts/package_offline.py
```

QA mengedit tests/fixtures/launcher/package tooling tersebut saja. Defect source diberikan ke owner paket, bukan diperbaiki dengan edit paralel file milik owner lain. Dependency config Python milik BE dan npm milik FE; requests tests/tooling disampaikan kepada owner. Fixture/private oracle tidak menjadi import dependency produksi. Mock launcher menggunakan ports/DTOs, tidak mengubah wire demi mempermudah tests.

## Inputs, outputs, kontrak dan consumer

| Input | Output | Consumer |
|---|---|---|
| SC-01/02 manifest/events/frames | Fixture source/reader/writer contracts | BE/SD/FE |
| SC-03 detector/lifecycle | Independent geometry/rule/quality expected outputs | SD dan BE integration |
| SC-04/05 worker/assist | Stub job results, valid/invalid evidence/options/review fixtures | AI/BE/FE |
| SC-06 REST/WS | Current compatibility + additive profile assertions | BE/API adapter |
| SC-07 adapter/UI states | Mock-browser and real API parity scenarios | FE |
| Implementasi semua ports | E2E evidence/replay/outage/recovery results, actual execution manifest | Semua owner; hasil teknis dibedakan dari domain status |

Fixtures membawa input hash/schema/engine/config/layout/scenario/model versions dan expected outputs yang tidak dihasilkan oleh tested implementation. Float tolerance baseline mengikuti plan; arbitrary ASR quality thresholds tidak ditambahkan.

## Mock/stub/fixture dan tests lebih awal

Minimum bundle berlabel `SYNTHETIC / NOT OPERATIONALLY VALIDATED`:

| Bundle/variant | Isi minimum | Contract assertions |
|---|---|---|
| F-REPLAY-01 | SC-01 manifest, local geometry, TRACK/CLEARANCE records, 0/200/400 ms frames, coverage/source IDs | Timestamp/unit/order, actual frame <= seek target, immutable source/hash |
| F-QUALITY-01 | Sample 0, receive 500; missing→nominal→stale age >3000; invalid/no-route/out-of-order | Missing bukan zero/fresh; latest state tidak mundur; ack/dropout tidak resolve |
| F-GEOMETRY-01 | Body/route independent coordinates/intervals, stationary/rotated/tangent/disjoint/reciprocal cases | Full footprint, nominal vs buffer overlap, unknown exit |
| F-COMM-01 | SYN-COMM-01 paired metadata/audio atau stub transcript, SEG-TWR-006/EVT-CLR-021/EVT-TRK-088/ALRT-009, analysis/ref examples SC-05 | Valid evidence, receipt offset 350 ms, possible_link versus linked, no duplicate alert |
| F-AI-FAIL-01 | No-speech, null confidence, clipped/overlap/code-switching, unknown alignment, timeout/cancel/late duplicate, invalid/action-field output | Review-needed/unknown, cancelled attempt no commit, source replay unaffected |
| F-AUTH-01 | Scoped/expired/cross-source seats, baseline, evaluator replay capability | Server redaction/denial, source-read versus review-control token scope |
| F-REVIEW-01 | Raw/corrected revision, confirm/dismiss/unresolved, stale expected revision, same request ID retry | Append-only, exactly-once receipt, source unchanged |
| F-STREAM-01 | Repeated snapshot, sequence gap, auth expiry, source/assist independent sequences | Resync no fabricated deltas or fresh extrapolation |

Nama bundle adalah identifier dokumentasi; fixture files belum dibuat. Transcript-only stub tidak berpura-pura audio atau ASR model sudah berjalan. Canonical existing scenario IDs dari [catalogue](../../../backend/data/scenarios.json) meliputi overlap, safe_cross, stopped, hold_line, unauthorized, hold_violation, cancelled, delayed_goaround, reciprocal_departure, dropout, duplicate_command, replay_sync. Nama scenario bukan hasil test.

Contract fixtures/tests bisa dikerjakan seluruhnya menggunakan FakeSource/FakeDetector/FakeWorker/InMemoryEvidenceReader/FixtureReplayReviewAdapter. Integration assertion yang membutuhkan runtime riil dijadwalkan sebagai tahap verifikasi, bukan prasyarat desain atau urutan kerja tim.

## Integration scenarios dan failure cases

| Scenario | Langkah dan assertion utama | Runtime riil yang diperlukan |
|---|---|---|
| I-01 Synthetic replay | Import fixture, read frame/events, controls seek/pause/speed; source hash/order tidak berubah | BE; SD stub cukup untuk transport/storage |
| I-02 Observed detection | Seeded source dengan delay, SD port, archived predictions/alerts/evidence; independent oracle dibanding | BE+SD |
| I-03 Assist round-trip | Register synthetic audio, worker typed result, transcript/highlight/option refs, evaluator-only reads | BE+AI stub dulu; provider riil terpisah |
| I-04 Review correction | Raw ASR→correction→new revision→refresh/restart; idempotency/conflict, source immutable | BE+AI payload; FE untuk browser |
| I-05 Partial outage | Cancel/timeout/missing model, late/duplicate result, assist WS drop sementara source replay tetap usable | BE+AI worker boundary+FE |
| I-06 Scope/privacy | Participant/baseline/observer, cross-source refs/token expiry, no truth/future events/options leak | BE+FE; forged payload fixtures |
| I-07 Replay time | Seek between frames/same-time ordinals, source sample/receive/audio timestamps, unknown alignment | BE+FE; SD historical fixtures |
| I-08 Recovery/branch | Commit fault/retry, interrupted startup, compatible checkpoint restore; unsupported branch tetap bisa review | BE+SD; temp SQLite private checkpoints |
| I-09 Offline package | Provision model assets lebih awal, network disabled, cold launch synthetic bundle, replay/audio/read/error paths | Semua implementasi yang dipaketkan; stub profile tetap berlabel |

Full runtime E2E: synthetic import→source replay→observed detector frames→audio job→raw segments/candidates→evidence click→review correction→debrief/readback after restart. Tidak ada langkah option→clearance command. Native Python Playwright memakai instructor/evaluator serta unauthorized participant contexts; training role workflows plan §16.3 diuji terpisah bila UI training dibangun. Empat browser contexts satu host tidak menjadi bukti LAN multi-mesin.

## Cara menjalankan mock stack target

**Belum tersedia di repository dan tidak dijalankan pada tugas dokumentasi ini.** Launcher yang akan ditulis QA harus:

1. Membaca fixture version/hash dan synthetic label; menyediakan source/archive reader, detector stub dan worker stub sesuai ports.
2. Menjalankan BE composition dengan isolated temporary local storage/operator credential, mematikan automatic simulation clock untuk fixture seek tests bila perlu (`create_app(..., run_clock=False)` current tersedia untuk composition test).
3. Menyajikan additive mock HTTP/WS transport sesuai SC-06, bukan endpoint vendor atau provider live. Unsupported capabilities berstatus unavailable.
4. Menjalankan FE explicit fixture mode atau API mode menuju mock server; mode terlihat pada UI. Gunakan Vite proxy current ke localhost:8000 untuk API mode development; same-origin bundle pada package offline.
5. Membersihkan proses/temp data melalui lifecycle launcher; tidak membuat background service permanen dan tidak membaca operator key/source data riil.

Command usulan setelah launcher/fixtures ditulis:

```powershell
# Dari root repository; launcher baru milik QA, belum ada sekarang.
python scripts/run_mock_stack.py --fixture F-COMM-01
```

Launcher harus mendokumentasikan port/default/output sementara yang benar-benar diimplementasikan. Jangan mengklaim flag atau command ini sudah didukung. Alternatif FE-only berjalan melalui FixtureReplayReviewAdapter; tidak membutuhkan BE process. `npm run dev` di `frontend/` current adalah script yang ada, tetapi dashboard/mock selection belum diimplementasikan.

## Offline packaging boundary

TARGET package lokal memuat server/runtime dependencies yang telah dikunci/diprovision, frontend build same-origin, schema/config/engine/layout/scenario/model version manifest, synthetic fixtures dan model assets yang memang tersedia/diizinkan, launcher serta label known limitations. SQLite/audio privat di disk server lokal; file raw audio/checkpoints tidak masuk public static bundle.

Cold launch tidak download model atau mengaktifkan cloud provider. Model unavailable → explicit degraded panel, source review tetap tersedia. Port lokal/isolated LAN hanya untuk lab; no internet exposure/live feed config. Credentials dibuat lokal, tidak di-embed ke JS/fixture/release archive. Package source mitra/personnel tidak dibundel default. Model license/provisioning/hardware compatibility merupakan unknown teknis yang dilaporkan; stub package diberi label mock, bukan provider-ready.

Backup SQLite memakai mekanisme snapshot/backup konsisten bila WAL aktif; jangan menyalin hanya database utama dan menganggap semua accepted records tersimpan. Packaging test tidak menjadi operasi live readiness.

## Verification teknis / readiness-to-integrate

| Jenis check target | Command/cara setelah implementasi | Kriteria |
|---|---|---|
| Contract early | `python -m pytest tests/contracts` | Port/API/UI payload parity, invalid evidence/time/version/actions ditolak |
| Numerical/worker unit | `python -m pytest tests/unit` | Independent geometry/aging/lifecycle/reconcile/stub failure oracles |
| Backend integration | `python -m pytest tests/integration` | Temporary SQLite, auth/REST/WS/import/recovery/correction atomicity |
| Frontend type/build | Dari `frontend/`: `npm run typecheck`, `npm run build` | Setelah missing UI/tooling dilengkapi; typed adapter/schema consistency |
| Browser mock/integrated | `python -m pytest tests/browser` memakai native Python Playwright scripts | Real UI actions/evidence/ref links/failure states; source immutable |
| Offline package | `python scripts/package_offline.py` lalu cold-run paket dengan network disabled | Manifest/provisioning/no download/private asset boundary; flag/output detail ditulis saat implementasi |

Semua path tests dan scripts pada tabel adalah **usulan**, belum ada; commands tidak dijalankan sekarang. Setelah checks relevan lulus, perluas hanya jika perubahan/failure/unknown membutuhkannya. Laporkan command, exit/result, fixture versions, model/hardware, source mode, limitations dan artifacts nyata. Jangan mencatat tests “passed” dari inspeksi source.

Performance targets hanya berasal plan §16.4–16.6: numerical tolerance, detector timing, delivery/render/reconnect/sync/endurance dengan environment manifest. Sensor delay, compute, persistence, delivery/render dipisah. Localhost tidak dianggap LAN result. WER/critical-slot/candidate FP/FN dilaporkan per corpus/profile/model; thresholds kualitas belum ditentukan. Human review/fidelity mitra tetap belum tervalidasi meskipun contract/E2E lulus.

Readiness-to-integrate: fixture semantics konsisten, tests mandiri bisa memakai stubs, outputs semua paket diuji pada port yang sama, runtime failures tidak memalsukan success/source authority, dan suite integrasi menunjukkan hasil aktual ketika komponen tersedia. Tidak memerlukan approval/sign-off atau review board.

## Asumsi dan unknown

**ASSUMPTION:** pytest/httpx/native Python Playwright sesuai stack target; fixture/profile identifiers di atas cukup untuk pembangunan contract tests awal. Mocks memiliki semantics current/proposed terpisah, tidak menutupi API yang belum ada.

**UNKNOWN:** tool/runtime installs dan dependency locks lengkap, actual package size/hardware/performance, codec/assets/license, partner ground truth/timebase/permissions. QA tidak menambahkan numerical quality claims atau provisioning sukses sebelum diuji.
