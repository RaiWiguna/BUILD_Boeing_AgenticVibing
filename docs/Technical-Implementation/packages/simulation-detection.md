# SD — Simulation/detection

**Owner-role:** Simulation/Detection. **Status:** `CURRENT_SOURCE` statis dan `TARGET/PROPOSED_CONTRACT`, 3 Oktober 2026. [Master](../README.md) · [Shared contracts](../shared-contracts.md).

## Objective dan output

Menyediakan synthetic replay source dan deterministic observed-only analysis yang dapat diuji tanpa server/SQLite/UI/AI. Output untuk BE: timestamped source observations, versioned public geometry/config, `DetectionResult`, serta lifecycle transition policy. Output untuk AI/FE melalui BE: evidence-backed predictions/alerts/quality, tanpa private truth. Output untuk QA: known scenario behavior dan numerical boundary cases; oracle tidak dibuat oleh detector yang dinilai.

## CURRENT/TARGET dan scope

| Label | Kondisi |
|---|---|
| CURRENT_SOURCE | Seeded Simulator mengintegrasikan mobiles tiap 100 ms; sampling/delay/noise/dropout; detector Shapely footprint dan interval; Session mengelola lifecycle |
| CURRENT_SOURCE | Detector hanya mendapat Track/Clearance inputs, tetapi mengimpor global LAYOUT dari scenarios; Session menentukan expected_ids dari simulator roster |
| TARGET | Explicit geometry/coverage/config input dan port murni; ordering/rejected observations; reproducible numerical fixtures; truth/observation/oracle isolation |
| UNKNOWN | Site-specific protection geometry/SOP/movement fidelity; mitra replay/time drift, independent domain-reviewed ground truth |

Included: synthetic truth clock/channel, public source adapter, geometry/prediction/rules, quality/uncertainty, lifecycle policy dan experimental complexity formula. Excluded: HTTP/storage/token orchestration, audio/ASR/options, rendering, new operational thresholds/procedures, feed fusion/live interfaces. Clearance terstruktur input berasal dari simulator/session; entity transcript tidak menjadi Clearance.

## Context packet

- [simulator.py](../../../backend/simulator.py): `sample/step/delivered/respond/checkpoint/restore`, seed/RNG, queues dan response delays.
- [scenarios.py](../../../backend/scenarios.py) dan [scenarios.json](../../../backend/data/scenarios.json): public layout, scenario metadata, private variants/actions dan 12 IDs.
- [detection.py](../../../backend/detection.py): footprint/expanded_area/predict/threshold_eta/detect/task_complexity.
- [models.py](../../../backend/models.py): Track/Clearance/SimulationConfig current; read-only bagi SD, owner BE.
- [session.py](../../../backend/session.py): baca `evaluate/advance/checkpoint` untuk memisahkan lifecycle; modifikasi oleh BE.
- [Plan](../../Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md) §7–11, §15.1–15.6, §16.2–16.6: clocks/unit, geometry/interval/rules, independent oracle, target acceptance.
- [AI addendum](../../Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md) §1.2 dan §5: jangan menduplikasi alert; paired synthetic audio/event fixture target.

Tidak ditemukan tests existing. Performance/numerical checks di dokumen target tidak menjadi hasil ukur source.

## Modul/file ownership

SD memiliki `backend/simulator.py`, `scenarios.py`, `detection.py`, `data/scenarios.json`. Modul baru usulan: `backend/geometry.py` (public layout/geometry, tanpa catalogue privat), `backend/detection_contracts.py` (SC-03 input/result), `backend/synthetic_source.py` (SC-01 adapter), `backend/alert_lifecycle.py` (pure lifecycle policy).

SD tidak mengedit `models.py/session.py/app.py/storage.py`. Perubahan config/contracts diserahkan ke BE; BE memasang SD lifecycle port di Session. Detector baru menerima geometry/config/coverage eksplisit, bukan mengimpor private scenarios atau state server. Synthetic source boleh membaca private simulator; exported records hanya sampled/delivered public fields. Private checkpoints/truth diserahkan melalui evaluator boundary BE, tidak via `ReplayEventSource.read`.

## Inputs, outputs, kontrak dan consumer

| Interface | Input | Output / consumer |
|---|---|---|
| SC-01 `SyntheticReplayEventSource` | Private scenario, seed, sensor config; controls synthetic-only | Manifest/public layout dan source records untuk BE; source identity/observed/receive times |
| SC-03 `DetectorPort.evaluate` | Observed Track/Clearance, now_ms, config, runway_open, previous tracks, layout, coverage-derived IDs | Predictions, deterministic candidates, runway quality untuk BE |
| SC-03 `AlertLifecyclePort.update` | Previous alert set, DetectionResult, simulation time | Alerts + transition events untuk BE persistence/stream |
| Complexity pure function | Role-scoped observations/tasks/channel spans dan config | Experimental score/components/model_version untuk BE/FE |

Existing rule strings: `ARRIVAL_OCCUPANCY`, `DEPARTURE_OCCUPANCY`, `HOLD_VIOLATION`, `CLEARANCE_INCONSISTENCY`, `CLOSED_RUNWAY`, `TRACKING_DEGRADED`, tambahan `SWEPT_OCCUPANCY`. R01–R06 plan adalah mapping requirements; jangan rename strings existing tanpa adapter/version. Candidate deterministic bukan opsi AI.

Prediction intervals relatif calculation time. Nominal overlap `max(0, min(exit)-max(entry))`; buffer/error range terpisah dari nominal overlap. `threshold_eta_s` bukan protection-entry time atau collision time. Konfigurasi `position_error_m`, `speed_error_fraction`, `buffer_s` adalah asumsi eksperimen, bukan confidence interval statistik.

## Mock/stub/fixture mandiri

Minimal fixtures tidak membutuhkan Archive/FastAPI:

| Fixture | Input penting | Oracle independen / tujuan |
|---|---|---|
| Track SC minimum | Observe 0, receive 500, stationary outside hold area | Missing sebelum receive; fresh pada age 3000; stale pada 3001 |
| Stationary inside/outside | Known body/heading/layout, speed 0 atau near-zero | Inside `exit_unknown`; outside tidak fabricated occupancy |
| Footprint edge/rotation | Analytic rectangle coordinates, body rear masih inside | Full footprint exit; tangent/edge tidak hilang karena center point |
| Piecewise route | Fixed route distances/speed dan multi-segment entry/exit | Interval/reference dihitung formula terpisah; disjoint intervals/route ends inside |
| Pair overlap / buffer-only | Interval a/b authored | Nominal overlap versus error/buffer-only; reciprocal directions satu physical resource |
| Hold/cancel/go-around | Recorded clearances dan delayed response observations | Request bukan permission; cancel tidak menghilangkan occupancy; response baru terlihat lewat observed state |
| Dropout/unknown route | Active prior threat + stale/missing sample | Quality degraded, tidak false-resolve/clear |
| Same-time/out-of-order | Stable ordinals dan sample times yang berbeda | Source log lengkap, state terbaru tidak mundur |
| Independent source ID | Coverage source publik, private truth ditambah tanpa changing observations | Detector output tidak berubah jika future scenario/hidden truth berubah |

QA kelak memegang canonical files/expected labels; SD dapat mulai dari inline fixtures dan stub event consumer yang hanya mengoleksi output port. Canonical scenario IDs existing diseleksi dari catalogue, bukan dianggap masing-masing telah lulus test. `duplicate_command` dan `replay_sync` menggunakan base variants; verifikasi concurrency/replay berada BE/QA, bukan bukti dari nama scenario.

## Alur utama

1. Synthetic simulator menggerakkan truth dengan fixed-step, seeded noise dan configured response delay. Pause menghentikan simulation clock; changing playback speed tidak mengubah fixed-step physics.
2. Sample menyalin truth saat sampling, memisahkan private route progress/future actions/RNG dari Track. Delivery mempertahankan sample time dan receive schedule.
3. Source adapter mengeluarkan record valid sesuai SC-01. Roster coverage publik tersedia tanpa future actions. Late packets dicatat; reducer BE mempertahankan current/previous per source.
4. Detector memvalidasi available observations, geometry/config dan timestamps. Invalid/missing/nonfinite tidak dipakai menghitung nominal precision; issue kualitas dilaporkan.
5. Hitung physical occupancy dari footprint dan predicted intervals dari remaining declared route/current speed, termasuk unknown exit, phase exemptions dan age correction. Jangan membaca planned speed/go-around di future simulator queue.
6. Rules membedakan physical interval, permission inconsistency, hold violation, closed runway dan quality. Evidence IDs/ages/calculated time/model/config/layout version tetap dapat ditelusuri lewat BE.
7. Pure lifecycle memutakhirkan same dedup incident, immediate escalation, downgrade/resolution tiga detik simulasi dengan evidence memadai; acknowledgement terpisah. BE membuat event IDs/persist dan publish.

## Failure/degraded cases

- Stale/missing/incomplete route membuat coverage/quality unknown; last-known occupancy tetap diberi label, bukan fresh observation. Tracking loss tidak memberi bukti clear.
- Nol speed di runway mempertahankan occupancy dan unknown exit; route berakhir di protection tidak berarti keluar pada horizon.
- Invalid polygon/negative dimensions/nonfinite/unit mismatch mengembalikan quality/error, tidak safe fallback. Persistent rule failure dilaporkan BE untuk pause target; SD tidak membuka logger/storage global demi mengubah sesi.
- Swept transit dapat menghasilkan uncertain occupancy antar-sample; jangan mengklaim simultaneous occupancy presisi tanpa bukti.
- Duplicated/stale samples tidak membentuk previous/current pairs salah; test harus mencakup moving fast across hold line.
- Missing structured clearance tidak meniadakan occupancy. Low visibility adalah konteks, tidak otomatis membuat surveillance dropout.
- Incompatible layout/config/version tidak diproses dengan geometry synthetic global sebagai fallback untuk replay mitra.

## Verification teknis / readiness-to-integrate

1. Unit fixtures untuk clocks/units/sample-delivery/pause/speed/seed repeatability; checkpoint restore termasuk RNG, queue dan pending responses. Uji state/log normalization mengabaikan UUID/wall timestamps saat membandingkan repeatability.
2. Analytical ETA error target ≤1e−6 s pada fixture sederhana dan movement interval tolerance satu tick 100 ms berasal dari plan §16.4. Ini target yang diuji kelak, bukan hasil ukur sekarang.
3. Footprint rotated/full-exit, multi-segment/disjoint route, horizon/unknown exit, reciprocal direction, buffer-only, cancellation dan delayed go-around sesuai independent oracle.
4. Semua rule/evidence referensi dapat di-resolve pada source scope; prediction calculation time/units/version tersimpan. Private future plan/benchmark labels tidak ada pada detector import graph/payload.
5. Lifecycle ack/dropout tidak resolve; escalation/downgrade same-time/pause behavior sesuai plan §10.3, termasuk unknown data pada active threat.
6. SD port berjalan tanpa BE/AI/UI, lalu BE integration memakai signature/shape yang sama. Same-time source records tidak memecah deterministic state.
7. Performance detector p95 <50 ms pada workload baseline plan §16.5 diukur tersendiri ketika runtime tersedia, dengan hardware/config/sample manifest. Jangan mencampur deliberate delay, SQLite atau UI rendering.

Readiness tidak menyatakan review pakar atau validasi operasional. Benchmark recall/false-warning plan memerlukan adequate-observation strata dan oracle independent; unit fixture lulus tidak membuktikan target benchmark tercapai.

## Asumsi dan unknown

**ASSUMPTION:** synthetic local layout current dan lab SOP dipertahankan sebagai baseline bertanda belum tervalidasi. Source current menggunakan body 2D dan sederhana phase/route; tidak ada klaim aircraft maneuver fidelity.

**UNKNOWN:** layout/safety margins/SOP vendor, source coverage dan sample ordering, domain-reviewed model/labels. Addendum paired SYN-COMM-01 belum ada pada catalogue/source; fixture authored tidak boleh disebut event/log simulator mitra.
