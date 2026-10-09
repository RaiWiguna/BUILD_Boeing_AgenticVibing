# Synthetic evaluation protocol — baseline-1

Tanggal 8 Oktober 2026. Technical research only; NOT_DOMAIN_VALIDATED. No benchmark result is claimed by this protocol.

## Inputs and truth separation

Application inputs: `tests/fixtures/manifests`, `audio`, `events`, `layouts`, and labeled provider mocks. Evaluator-only script semantics/labels live in `evaluation/fixtures/labels`; geometric/time expected outcomes live in `evaluation/fixtures/oracles`. Neither is imported by application/domain/providers/tools. Contract examples with origin MOCK are harness records, not STT gold.

Speech asset `hold-short.wav`: macOS say/Samantha en_US, rate 150, PCM LEI16 16kHz mono, fictional project-authored callsign/runway conversation. Initial generation command (re-generation may change waveform across OS/voice versions):

```sh
say -v Samantha --file-format=WAVE --data-format=LEI16@16000 -r 150 -o tests/fixtures/audio/hold-short.wav 'Flow lens two one four, hold short of runway two seven. Holding short of runway two seven, Flow lens two one four.'
```

The checked-in hash is authoritative. Synthetic non-sensitive input, no real speaker or corpus. Pronunciation/time-span audit PENDING: script intention is NOT gold transcript and cannot be used to claim WER/critical-slot accuracy. `silence.wav` is 1-second 16kHz PCM silence for no-speech failures. Inline STT can receive the actual waveform later, after operator credential/budget readiness. A/B are not waiting for one another's generator.

Contract fixtures preserve known transform/clock; synthetic event availability includes known, delayed and unknown cases. Geometry layout is fictional meters/XY, no operational chart. Independent oracle examples use hand-derived rectangle overlap and interval intersection, not application calculation.

## Mandatory cohorts and expected outcomes

| Cohort | Cases to implement in A/B | Expected evaluation behavior |
| --- | --- | --- |
| Geometry S01–S03 | Crossing before arrival, overlap, stopped vehicle in protection | Interval/footprint resource constraints; stopped is not clear |
| Geometry S04–S06 | Hold line without movement, crossing without instruction, hold-short violation | Physical occupancy separate from permission; no motion uncertainty |
| Geometry S07–S10 | Cancel occupied, delayed go-around, bidirectional runway, dropout | Cancellation/report does not remove physical occupancy; dropout preserves unknown |
| Transport S11–S12 | Duplicate/concurrent mutation, seek/reconnect/multiclient | One local accepted effect, reproducible snapshot/resync |
| Audio | Noise/overlap/gaps, clipped negation, wrong runway/callsign, compound/conditional/correction | Preserve critical-slot ambiguity and time mapping |
| Association | Interleaving entities, similar callsigns, late readback, changed alias, wrong-target correction, cancellation | No forced wrong accepted pair; explicit alternatives |
| Failure | 429/timeout/refusal/malformed/schema-valid unsupported/injection/invalid evidence | Typed unavailable/partial/rejected; no fake content |
| Scope | Cross-session/run/truth/raw media/unauthorized tool | Zero successful forbidden accesses |
| Recovery | Atomic import failure, upgrade/restart, late result, disk full, expiry/purge/restore | No partial readable commit; preserve durable history |

The table records baseline requirements. A08.3 now supplies source-observed lab S01–S10 tests with independent time/geometry expectations ([technical evidence](../../docs/testing/a083-evidence.md)); S11–S12 transport technical checks are in A03/A07. This does not complete Phase10 cross-boundary/provider/domain evaluation. Actual input/output labeling is completed in owner phases 3/5/7/8/10. Baseline already supplies waveform, events, layout, invalid contracts and small independent numeric oracles. Additional seeded/noisy/held-out scenario generators, real B/provider integration, and held-out benchmark runs remain downstream work.

## Split and measurements

Before tuning, register immutable fixture/source hashes, seed, split and label provenance. Seeded additional scenario evaluation plans 100 runs, excluding S11/12 from physical-hazard denominator. Split source-session/date/speaker/airport where metadata exists; synthetic families and voice variants must not leak between tuning/held-out. Current TTS fixture is tuning only; no held-out result yet.

Manual pronunciation and time audit precedes waveform gold labeling. Freeze thresholds before final held-out evaluation. Report WER additionally to callsign/runway/action/condition/negation errors, timestamp error, accepted wrong-pair rate, ambiguity/abstention, finding precision/recall with denominators. Track STT and association errors separately. Record model/API/SDK/schema/prompt/reducer/rule/config/input versions, latency p50/p95 and usage. Never tune on final held-out results to manufacture pass. Domain review is separate.
