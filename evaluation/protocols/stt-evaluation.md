# B03 waveform annotation and alignment protocol — b03-evaluation-1

9 October 2026. Preparation only, NOT_DOMAIN_VALIDATED; no benchmark executed.
Run `.venv/Scripts/python.exe scripts/evaluation_stt.py` for the bounded readiness
audit. `stt-plan.json` contains tuning input and a **planned** held-out acquisition,
not an existing held-out corpus. Empty verified cohorts mean no claimed coverage.

The hold-short waveform remains synthetic TTS / NOT_GOLD. Script intention and
MOCK SDK responses are never pronunciation truth. Runtime, observers, providers
and tools must not load evaluation manifests, labels, scripts or scenario truth.
Only an offline evaluator may join outputs to these records.

Before scoring, the annotation owner acquires independently licensed synthetic or
roleplay audio, records source hash/rights/cloud transfer permission/voice/session/
family/channel/gaps, and assigns each family to tuning OR held-out before tuning.
No identical waveform, speaker/session family or transformed copy crosses splits.
The current Samantha hold-short family is tuning only. Freeze normalization,
thresholds, matching procedure and split hashes before opening held-out outputs.

Two independent reviewers listen to the **actual waveform**, then adjudicate
disagreements. Store reviewer IDs, UTC review dates, annotation version/hash and
adjudication record. A domain reviewer separately approves aviation interpretation;
pronunciation audit alone never grants DOMAIN_REVIEWED or operational validation.
Annotations retain verbatim audible words, uncertain alternatives, unintelligible
and clipped spans, explicit ambiguity, channel and source sample/rate boundaries.
Do not infer clipped negation or repair callsigns from the intended script.

Each word and segment gets independently marked source boundaries plus uncertainty.
Each callsign/runway/action/condition/negation slot gets a verbatim quote, token
span, waveform range, audible value or AMBIGUOUS/MISSING/NOT_EVALUABLE, and reviewer
decision. Correction utterances preserve original and replacement, with no silent
normalization. Required cohorts: callsign, runway, action, condition, negation, clipped boundary,
overlap, repetition, gaps, channels, correction, ambiguity, word and segment alignment.
Each split needs audited cohort coverage; planned cases are not denominator entries.

Real output provenance must bind original audio/derivative/chunk hashes, model,
locale/region/recognizer/features, SDK/API/config hash, raw response hash and attempt
usage/latency. Preserve unknown clock and missing offsets; source word alignment can
be measured without inventing session time. Exact-overlap canonical words and raw
hypothesis transcript are separate outputs, never a claimed stitched transcript.

Default preflight deliberately emits **metrics=null** even when manifest fields
claim audit: manifest assertions alone do not prove artifact contents. The offline
loader/scorer now exists in `scripts/stt_scoring.py`; it is independent of Package A
and does not send requests to Google. Run from the repository with Python3.12:

```powershell
.venv/Scripts/python.exe scripts/evaluation_stt.py
.venv/Scripts/python.exe scripts/evaluation_stt.py --bundle evaluation/reports/private-b03/bundle.json
```

The second command is for actual reviewed artifacts when available; no such bundle
exists yet. All artifact references must be relative to the bundle directory (or
explicit `--artifact-root`), with SHA256. Absolute paths, traversal, drives, URLs,
ADS and resolved junction/symlink escapes fail closed. Malformed/missing artifacts
emit only BLOCKED/metrics=null with a safe code; no transcript, exception or path.
Bounds: bundle256KiB/64entries; label256KiB; raw8MiB; binding512KiB; receipt16KiB;
source audio32MiB; chunk9,999,999bytes; 512tokens/128segments per case. Larger corpora
need separately reviewed bounded bundles. Keep them private in ignored reports,
never runtime fixtures, frontend or provider prompts.

Schemas are strict Pydantic `Label`, `Receipt`, `Entry`, `Bundle`; JSON Schema is
available using each class's `model_json_schema()` for annotation tooling. These
are evaluator schemas, not additions to frozen wire contracts1.0.0. Label version
`b03-waveform-label-1` records case/session/family/speakers/split, original source
and chunk hashes, source UUID/channel/source nanosecond range, rights-record ID,
annotation revision, transcript, words, segments, slots/cohorts, two distinct
waveform reviewers with UTC dates, independent adjudicator/date/record and
NOT_DOMAIN_VALIDATED. Every word/segment has text, optional source range, explicit
ambiguity, alternatives and clipped flag. Slots have kind, zero-based half-open
token indices into the transcript, exact quote, source range and ambiguity. Words
and segments must reproduce transcript tokens; slot quotes must match their span.
Clear slots cannot cover ambiguous/clipped words. Corrections retain both spoken
original/replacement as separate words/slots, not a repaired transcription.

`b03-google-receipt-1` requires operator ID, execution/review UTC times, real
execution evidence-record ID, raw/response/config/binding hashes, SDK/APIv2,
one call, attempted duration, latency and explicit real-execution attestation.
The operator must verify actual execution evidence; setting an enum or boolean
does not authenticate Google. Raw JSON and authoritative AuthorizedChunk bind the
source/chunk/scope/config. The loader verifies file hashes, source UUID/channel/
range/session and receipt bindings, then reconstructs every raw field from the
original protobuf and B02 preparation through the existing private validator.
This is consistency checking, not a cryptographic Google-origin signature. Trusted
private acquisition and human receipt review are still required. MOCK receipts and
TEST_ONLY labels never unlock benchmark loading. Local SDK tests use TEST_ONLY IDs
and labels even when testing the real-origin receipt schema; no benchmark is run.

`b03-scoring-bundle-1` freezes normalization/protocol record and two reviewers after
label adjudication and before provider execution. Each entry references label/raw/binding/receipt/source_audio/
chunk_audio files. Full validation occurs before metrics. Each split needs all14
audited cohorts. Case IDs must be unique; identical source/chunk hashes, session,
family or any speaker cannot cross tuning/held-out, including transformed copies.
Review leads must assign stable family/speaker IDs; hashes cannot detect unrelated
files falsely assigned different metadata. Acquisition/review evidence supplies that
authority. Thresholds and domain interpretation remain annotation-lead decisions;
SCORED describes arithmetic only and never automatically passes B03 or a gate.

Frozen normalization is Unicode casefold + whitespace split, preserving punctuation,
numbers and callsigns. Levenshtein ties choose diagonal, deletion, insertion. WER
reports S/D/I and reference-word denominator per chunk; zero reference yields null.
Ambiguous/clipped cases are excluded wholesale from WER with excluded-word counts,
avoiding pseudo-gold partial text. Critical-slot metrics count lexical token-span
errors and eligible/ambiguous/missing/not-evaluable separately; these are not intent
or semantic-slot accuracy. Word/segment exact-text matches report independent start/
end absolute source-time errors (median, nearest-rank p95, max, matched denominator),
unmatched spans, missing reference/prediction timing and excluded ambiguous/clipped
spans. Unknown session clocks stay explicit. Segment prediction boundaries use
enclosing first/last word offsets only when all words have offsets; a result end
alone cannot create a start. Top alternatives only; no stitched/deduplicated corpus
claim. Overlapping chunks are per-chunk cases, never silently pooled as unique audio.
Synthetic timing unit tests are engineering acceptance, not timestamp-quality results.

Current blockers: no audited waveform labels, no acquired held-out audio/cohort
coverage, no real provider outputs, no approved scoring thresholds/domain reviewer.
Owner: annotation/evaluation lead for corpus/labels/review; cloud operator for real
outputs; Paket B maintains the implemented loader/scorer and runs it after reviewed
artifacts exist. No WER,
critical-slot accuracy or timestamp quality benchmark is reported at this stage.
