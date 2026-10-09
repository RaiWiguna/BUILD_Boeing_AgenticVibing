# B04/B05 offline semantic evaluation — b045-semantic-1

9 Oktober 2026. Tooling evaluator saja; **NOT_DOMAIN_VALIDATED**. Default benchmark
eksternal **BLOCKED**, metrics **null**. Threshold resmi belum disepakati:
**UNSET**, acceptance_decision **null**, integrated readiness **false**.
Synthetic labels tidak menjadi gold. Tidak ada reviewer nyata, corpus audited,
provider output nyata atau domain result yang dibuat oleh tooling ini.

## Entrypoints dan batas data

```powershell
uv run --locked --python .venv/Scripts/python.exe python scripts/evaluation_semantic.py
.venv/Scripts/python.exe scripts/evaluation_semantic.py --schema
.venv/Scripts/python.exe scripts/evaluation_semantic.py --test-only --bundle evaluation/fixtures/semantic-test-only.json
.venv/Scripts/python.exe -m pytest tests/analysis/test_semantic_scoring.py -q
```

`scripts/semantic_scoring.py` hanya mengimpor stdlib/Pydantic; runtime tidak
mengimpor evaluator ini. `--schema` mengekspor JSON Schema evaluator, terpisah dari
frozen contracts1.0.0. `semantic-test-only.json` berisi tabel arithmetic dengan
review identity **TEST_ONLY-NOT-A-PERSON**, bukan reviewed aviation labels.
Mode TEST_ONLY mengharuskan profile MOCK/calls0 dan tetap menampilkan nested
external_benchmark BLOCKED/metrics=null. Tanpa flag, fixture TEST_ONLY ditolak.

Untuk corpus yang nanti benar-benar diperoleh dan diaudit:

```powershell
.venv/Scripts/python.exe scripts/evaluation_semantic.py --bundle PRIVATE/audited-bundle.json --raw-output PRIVATE/acquired-outputs.json
```

Command terakhir **NOT_RUN**. `PRIVATE` adalah lokasi privat milik operator,
bukan data yang sudah ada. Hasil yang eligible hanya `DESCRIPTIVE_ONLY`, tanpa
verdict acceptance. Jangan menyimpan corpus/audio/reviewer nyata pada fixture
tracked. Rights/cloud transfer/retention dan acquisition tetap tanggung jawab
evaluation lead/cloud operator. Scorer tidak membaca credential atau memanggil SDK.

## Schema dan identity

Semua records strict, immutable, extra fields forbidden, finite-only. JSON input
menolak duplicate keys serta NaN/Infinity. Bundle dan acquired raw envelope masing-
masing maksimum8MiB;4096 annotations/predictions,8192 evidence references. IDs
wajib/nonempty/bounded, revision positif, UTC timestamps, SHA256 lowercase64hex.
Malformed bundle/IO/mode mismatch menghasilkan exit2/BLOCKED/metrics=null dengan
safe code; raw annotation/prediction dan exception tidak dicetak.

- `Scope`: session/run/revision, source/input SHA256, family, speakers, split
  TUNING/HELD_OUT, as_of_ms. Exact equality diperlukan antara annotation,
  prediction dan evidence. Source, input, family, session atau speaker yang sama
  tidak boleh melintasi split. Hash tidak mendeteksi transformed copies; acquisition
  owner wajib menetapkan family/speaker identity yang benar sebelum tuning.
- `Annotation`: unique case ID, subject ID, task, KNOWN/AMBIGUOUS/UNKNOWN, expected
  label/null, acceptable/required evidence IDs, earliest closure time, relevance
  output hash, reviewer records dan adjudication. Task mencakup speech-act,
  callsign/runway/action, negation/condition/correction/cancellation, association,
  open_loop, finding, brief_relevance dan option_relevance. Presence tasks memakai
  PRESENT/ABSENT; association menyimpan target ID serta relationship READBACK_OF,
  REPORT_FOR, CORRECTION_OF atau CANCELS. Task dan subject mengidentifikasi unit
  scoring yang harus ditetapkan annotation lead sebelum model execution.
- `Prediction`: case ID/scope, ANSWERED/UNKNOWN/ABSTAINED, value/null, evidence IDs,
  closure time bila CLOSED, raw subject-output hash serta relationship bila pairing.
  Missing prediction diperbolehkan dan dihitung sebagai MISSING; prediction tanpa
  annotation, ID duplikat, missing ID atau scope mismatch ditolak sebelum scoring.
- `Evidence`: unique ID, full scope, content hash, known available_ms≤as_of_ms.
  Dangling/cross-scope/unknown/future evidence ditolak. Evidence yang resolvable
  tetapi tidak termasuk annotation support dihitung unsupported; tidak dianggap
  benar hanya karena ID ada. Required evidence harus seluruhnya disertakan.
- `Review`: reviewer ID, experience record, UTC date, audit record ID. Relevance
  wajib memiliki review dan hash output spesifik; nilai prediction tidak menjadi
  self-grade. Unresolved reviewer judgment memakai UNKNOWN/AMBIGUOUS/null.
- `Provenance`: model/API/SDK/prompt/schema/config versions/hashes, calls, execution
  time/record, raw artifact hash, canonical normalized predictions hash dan
  operator review. Canonicalization: UTF-8 `json.dumps(sort_keys=True,
  separators=(",",":"),allow_nan=False)`; list order dipertahankan.

Audit mode mensyaratkan GOOGLE/calls>0 dan operator review setelah execution;
protocol review/rubric sebelum execution, dua annotation reviewers berbeda dan
adjudicator ketiga. Label non-relevance harus adjudicated sebelum protocol freeze;
relevance dinilai setelah output diperoleh. Kedua splits wajib ada. Current
domain_status sengaja tetap NOT_DOMAIN_VALIDATED; domain approval memerlukan
protokol/version/keputusan manusia berikutnya, bukan enum yang dinaikkan otomatis.

Raw envelope: satu JSON object `{"outputs": {"case-id": RAW_SUBJECT_OUTPUT, ...}}`.
SHA256 seluruh file harus cocok raw_output_sha256; exact prediction ID set harus
cocok; canonical hash tiap raw subject output harus cocok output_sha256.
Per-case raw response/subset dan normalized projection disiapkan acquisition owner
tanpa evaluator truth. Operator membandingkan projected labels/evidence ke output
asli dan menandatangani audit record yang mengikat normalized predictions digest.
Hash/reference/date/enum adalah consistency checks, **bukan autentikasi Google**
atau bukti reviewer/rights. Trusted acquisition, actual source/evidence contents,
review records dan projection fidelity tetap membutuhkan audit manusia. Input
raw/external yang mengklaim GOOGLE belum pernah dipakai sebagai benchmark sesi ini.

## Denominator dan perhitungan

Unit = satu case/task/subject/as-of. Untuk compound actions, reviewer menetapkan
case terpisah per action ordinal. Tidak ada fuzzy normalization/LLM self-grading.
Condition dan lexical slots dibandingkan exact canonical reviewer value; convention
kanonisasi corpus harus dibekukan dalam rubric_record sebelum tuning. Correction
dan cancellation presence terpisah dari relationship/target association sehingga
cue yang benar tetapi target salah tetap tercatat sebagai wrong pairing.

Metrics selalu terpisah per split/task. Counter labels KNOWN/AMBIGUOUS/label_unknown
terpisah dari output answered/abstained/prediction_unknown/missing.

| Metric | Numerator / denominator |
| --- | --- |
| exact_accuracy | ANSWERED value + relationship tepat / seluruh KNOWN labels; missing/unknown/abstained output salah pada denominator ini |
| coverage | ANSWERED / seluruh annotations, termasuk ambiguous/unknown labels |
| wrong_pair_rate | Salah target atau relationship / ANSWERED pairing pada KNOWN labels |
| closure_precision | CLOSED tepat, tidak premature, seluruh required support ada dan tidak ada unsupported citation / CLOSED predictions pada KNOWN loop labels |
| premature_closures | CLOSED sebelum earliest_close_ms pada expected CLOSED; dilaporkan sebagai count |
| false_closures | CLOSED pada expected OPEN; dilaporkan sebagai count |
| finding_precision | PRESENT benar / PRESENT predictions pada KNOWN finding labels |
| finding_recall | PRESENT benar / expected PRESENT; missing/unknown/abstained output adalah miss |
| supported_finding_precision | PRESENT benar + required support lengkap/tanpa unsupported citation / PRESENT predictions pada KNOWN labels |
| reviewer_relevance | Reviewer menilai RELEVANT / outputs dengan KNOWN reviewer relevance dan prediction yang hash-nya cocok |

AMBIGUOUS/UNKNOWN labels tidak masuk accuracy/precision/recall denominators;
unassessable answers/closures/findings dilaporkan tersendiri. Abstention pada label
AMBIGUOUS dilaporkan, tanpa diklaim classification correctness. Tidak menjawab
relevance case dihitung missing, tidak masuk relevance fraction; unknown reviewer
rating tidak menjadi irrelevant. Zero denominator selalu null. Exact loop status
accuracy dapat benar meskipun closure premature; closure_precision/counts adalah
penilaian timing/evidence yang terpisah. Wrong-pair rate selalu dibaca bersama
coverage/missing/abstention sehingga abstain-all tidak tampak sebagai accuracy1.

Fixture oracle ditabulasi terpisah: pairing1 benar/1 salah/1 missing pada3 known,
wrong-pair1/2; loop2 status cocok/4known tetapi hanya1 correct supported closure
dari3attempts (1premature,1false); finding2/3precision,2/3recall,1/3supported
precision; brief relevance1/2, options0/1. Ini uji arithmetic **TEST_ONLY**, bukan
angka kualitas produk. Tests juga menguji mode isolation, leakage, IDs/scope,
provenance/hash/date/schema/evidence, wrong relationship dan reviewer self-grade.

Threshold research/acceptance resmi tetap UNSET. Evaluation/domain lead harus
membekukan corpus-specific rubric, cohort coverage dan thresholds bersama protocol
version baru sebelum menghasilkan acceptance decision. Tooling ini tidak
menghasilkan PASS/FAIL produk, menutup B03–B06, atau menaikkan integrated readiness.
