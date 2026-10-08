# Requirement and source audit — Phase 0.1

Tanggal: 8 Oktober 2026. Inspeksi statis pada candidate parent fb1e1f7; source historis tidak dipulihkan. Audit bukan runtime/provider/domain acceptance.

## Functional coverage

| FR | Capability | Priority | Owner/phase | Disposition |
| --- | --- | --- | --- | --- |
| FR-01 | Setup sesi, import audio/event, provenance dan permission profile | P0 | A 2–3 | Build-new setelah foundation; belum implemented |
| FR-02 | Replay audio/timeline, seek, pause, speed, as-known/debrief | P0 | A 4 | Build-new setelah foundation; belum implemented |
| FR-03 | Google STT dan transcript review | P0 | B 6–7 | Build-new setelah foundation; belum implemented |
| FR-04 | Intent understanding dan parsing dengan Gemini | P0 | B 8 | Build-new setelah foundation; belum implemented |
| FR-05 | Association callsign–instruction–readback | P0 | B 8.3 | Build-new setelah foundation; belum implemented |
| FR-06 | Memori per objek dan runway | P0 | B 8.4 | Build-new setelah foundation; belum implemented |
| FR-07 | Readback discrepancy dan critical-slot uncertainty | P0 | B 7/9.1 | Build-new setelah foundation; belum implemented |
| FR-08 | Open loops untuk request/report/coordination | P0 | B 8.4/9.1 | Build-new setelah foundation; belum implemented |
| FR-09 | Observed-movement conformance | P0 bersyarat data | A 5 + B 9.1 | Build-new setelah foundation; belum implemented |
| FR-10 | Evidence drawer dan source-quality states | P0 | A/B 3–9 | Build-new setelah foundation; belum implemented |
| FR-11 | Opsi offline untuk evaluator | P0 | B 9.2 | Build-new setelah foundation; belum implemented |
| FR-12 | Review/correction append-only | P0 | B 7.3/9.3 | Build-new setelah foundation; belum implemented |
| FR-13 | Journal, brief, export JSON/CSV/HTML | P0 | A/B 9.4 | Build-new setelah foundation; belum implemented |
| FR-14 | AI-assisted contextual question answering | P1 | B 9.5 | Scheduled P1; tidak deferred |
| FR-15 | Komunikasi: occupied audio time dan open-loop count | P1 | B 9.5 | Scheduled P1; tidak deferred |
| FR-16 | Auth, scoped permissions, audit, provider config | P0 | A 2/9.6 | Build-new setelah foundation; belum implemented |
| FR-17 | Recovery job, reconnect/resync, cached replay | P0 | A/B 4/6–9 | Build-new setelah foundation; belum implemented |
| FR-18 | Containerization, backup/restore, release manifest | P0 | A 9.6/10; delivery 15–17 | Build-new setelah foundation; belum implemented |
| FR-19 | Copilot pada simulasi berjalan dan microphone lab | Future/pending scope | Future | Excluded dari v1; scope decision terpisah |
| FR-20 | Operational shadow/live advisory | Future | Future | Excluded dari v1; scope decision terpisah |

## Acceptance coverage

Semua acceptance berikut tetap target; baseline tidak menandainya PASS. Tests foundation menutup acceptance Phase 1 sendiri.

| AC | Requirement | Acceptance target | Evidence phase |
| --- | --- | --- | --- |
| AC-01 | FR-01/16 | Import valid mempunyai manifest/hash/permission; forbidden cloud transfer ditolak sebelum provider call | Backend owner phases + integrated 10 |
| AC-02 | FR-02/17 | Audio/event seek konsisten, gaps terlihat, reconnect tidak menggandakan state, mode debrief/as-known berbeda | Backend owner phases + integrated 10 |
| AC-03 | FR-03 | Google STT real smoke lulus; hypothesis dan word/chunk ranges tersimpan; correction tidak menimpa raw STT | Backend owner phases + integrated 10 |
| AC-04 | FR-04 | Gemini real smoke untuk structured intent lulus; invalid schema/evidence/tool/as-of ditolak; unknown valid | Backend owner phases + integrated 10 |
| AC-05 | FR-05 | Interleaved callsign/correction/cancellation fixtures tidak membentuk wrong accepted pairing; ambiguity terlihat | Backend owner phases + integrated 10 |
| AC-06 | FR-06 | Memory rebuild reproducible pada same accepted events; instruction/readback/movement/review status terpisah | Backend owner phases + integrated 10 |
| AC-07 | FR-07/10 | Critical-slot mismatch menunjukkan kedua quotes/audio dan association; unclear slot tidak diberi certainty palsu | Backend owner phases + integrated 10 |
| AC-08 | FR-08 | Open loop hanya closed oleh evidence matching; timer versi lab dan channel coverage tercatat | Backend owner phases + integrated 10 |
| AC-09 | FR-09 | Sintetik hold-line/footprint case lulus; missing identity/clock/track/layout mengembalikan NOT_EVALUABLE | Backend owner phases + integrated 10 |
| AC-10 | FR-10 | Seluruh accepted finding mempunyai resolvable scoped evidence; source alert tidak dihapus/regraded AI | Backend owner phases + integrated 10 |
| AC-11 | FR-11 | Opsi memiliki evidence/preconditions/unknowns/review; insufficient context dapat menghasilkan nol opsi; tidak ada execute command path | Backend owner phases + integrated 10 |
| AC-12 | FR-12 | Review append-only mempunyai actor/reason/revision; stale dependents terdeteksi dan reanalysis tidak overwrite run | Backend owner phases + integrated 10 |
| AC-13 | FR-13 | Brief/export mempertahankan source labels/versions/unknowns dan permission; setiap factual item mempunyai ID bukti | Backend owner phases + integrated 10 |
| AC-14 | FR-16 | Cross-session/API/WS/audio/truth/tool negative cases seluruhnya menolak akses; secrets tidak masuk client/log | Backend owner phases + integrated 10 |
| AC-15 | FR-17 | STT/Gemini outage tetap memungkinkan cached replay; retries/cancel/late result/budget tidak duplicate commit | Backend owner phases + integrated 10 |
| AC-16 | FR-18 | Compose local dan VM smoke lulus, images/version config tercatat, migration/restart/restore teruji | Delivery 15–17 |
| AC-17 | NFR-01–10 | Baseline performance/isolation/durability measurements dilaporkan; gagal target diberi status jelas | Backend 10, frontend 14, VM 17 |
| AC-18 | §34.4 | Held-out benchmark mempunyai source split, manual/synthetic label provenance, critical-slot/wrong-pair/finding metrics | Backend owner phases + integrated 10 |
| AC-19 | §34.6 | Review domain diberi DONE hanya jika reviewer nyata dan hasil ada; jika belum, research release berlabel NOT_DOMAIN_VALIDATED | Domain reviewer terpisah; default NOT_DOMAIN_VALIDATED |
| AC-20 | §5.4 | Kapabilitas core pada §5.4 tercakup dan pemeriksaan relevan lulus; perubahan requirement wajib memiliki keputusan scope dan acceptance yang diperbarui | Backend owner phases + integrated 10 |

## Source disposition

| Existing input | Disposition | Static evidence / compatibility |
| --- | --- | --- |
| .agent PRD/rules/roadmap | Reuse sebagai target; metadata status diperbarui | Empat dokumen tersedia; roadmap newer sequencing governs |
| README/docs/ADR 0001 | Reuse/modify status | Struktur modular accepted; bukan aplikasi |
| backend/flowlens/* .gitkeep | Build-new source | Tidak ada implementation sebelum tugas ini |
| tests/scripts/contracts .gitkeep | Build-new harness/tooling/fixtures | Tidak ada suites/commands executable sebelumnya |
| frontend/deploy/.github .gitkeep | Keep reserved | Belum track yang boleh diimplementasikan |
| data/artifacts/evaluation reports | Keep private/ignored | Tidak ada DB/source/audio pengguna yang dimigrasi/reset |
| Historical operator-key/routes/archive | Explicit compatibility work milik A | Tidak direstore; Phase 2/4 harus membuktikan migration/deprecation disposition |
| Shared schemas/ports | Build-new Phase 1 | SDK/domain/storage internals di luar kontrak publik |

## Core risks and regression map

- Single writer/atomic accepted result: transaction ports dan reference rollback/receipt/event tests sekarang; production persistence/recovery Phase 2/6/10.
- Timing/availability: known/delayed/unknown fixture dan AS_KNOWN filtering sekarang; real replay/checkpoint reconstruction Phase 4/10.
- Truth isolation: evaluator-only directories dan no-import/no-wire-label checks; grant-based truth access Phase 2/10.
- Physical footprint/source authority: independent layout/oracles disiapkan; observed detector dan source alert lifecycle Phase 5, semantic assembly B9.
- Source rights/cloud/export: permission schemas sekarang; transport/provider eligibility Phase 3/6/7/8/9/10.
- Schema-valid semantic error: reference evidence checks sekarang, real semantic benchmarks Phase 7/8/10.
- Fixture waveform gold: pronunciation audit belum tersedia; script bukan gold dan benchmark belum dilakukan.
- No frontend/deploy sequencing drift: contract artifacts generation diperbolehkan; React/Compose tetap reserved.
