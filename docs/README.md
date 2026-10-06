# ATC FlowLens documentation map

Start with the repository [agent instructions](../AGENTS.md), then use this page to load only the context relevant to the task. The documents below have different roles; a presentation summary is not a second product specification.

## Authority and document roles

| Role | Canonical source | Use |
|---|---|---|
| Intended product, MVP scope, architecture, interfaces, and acceptance targets | [Rencana Teknis MVP](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md) | Normative target. Requirements are not proof that the feature is implemented. |
| AI advisory requirements, environment readiness, and coding prompt | [AI Assist Buddy Addendum](Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md) | Specifies offline partner-simulator replay and evidence-linked candidate options for MVP; live Tower/Ground advisory is a future gated objective, not current authorization or implementation. |
| Modular technical implementation blueprint authoring prompt | [Blueprint authoring prompt](Technical-Implementation/blueprint-authoring-prompt.md) | Reusable prompt for generating a master blueprint and parallel backend/replay, simulation/detection, AI harness, frontend, and integration/QA packets; documentation-only. |
| Modular technical implementation blueprint | [Technical Implementation Blueprint](Technical-Implementation/README.md) | Documentation-only master, shared contracts, and five workstream packets. Separates inspected source from target/proposed interfaces; supports parallel development with mocks, without claiming feature implementation. |
| Current repository implementation state | [Implementation Status](IMPLEMENTATION_STATUS.md) plus the source code | Dated static inventory. Inspect code and run the appropriate checks before making stronger claims. |
| CI branch verification and PR promotion | [CI/CD setup](CI_CD.md) and `.github/workflows/ci.yml` | Workflow source and manual GitHub settings; local configuration is not evidence of remote Actions runs or branch protection. |
| CI/CD requirement progress and run history | [CI/CD build log](Technical-Implementation/CI_CD_PROGRESS.md) | Living record of checks, decisions, failure analysis, local verification, and outstanding GitHub configuration. |
| Evidence about the ATC operating context | [Operational Reality Research](Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md) | Domain claims, sources, evidence limits, and research gaps. |
| Historical review | [Knowledge Review snapshot](Knowledge-Review/ATC_FlowLens_Knowledge_Review.md) | Archive and navigation only; it is not a current implementation report. |
| Background research | `General-Information/` | Earlier research notes, mostly dated 31 May 2026. Consult when useful; prefer the evidence register for current claims. |
| External communication | Proposal Markdown, mentor brief, slide narrative, HTML, PDF, and PPTX under `Proposal/` and `Knowledge-Review/` | Preserve as presentation/reference artifacts. They do not define software requirements. |

## Load the technical plan by task

Use the relevant section instead of loading all 1,500+ lines for every task:

| Task | Read these sections in the technical plan |
|---|---|
| Product purpose, users, training flow, or MVP boundary | [§1](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#1-tujuan-keputusan-awal-dan-cara-membaca-dokumen), [§4](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#4-pengguna-penerapan-dan-alur-latihan), [§5](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#5-ruang-lingkup-dan-prioritas-mvp) |
| AI advisory, offline replay, readiness gate, or standards gap | [AI Assist Buddy Addendum](Knowledge-Review/ATC_FlowLens_AI_Assist_Buddy_MVP_Prompt.md), [Operational Reality Research](Knowledge-Review/ATC_FlowLens_Operational_Reality_Research.md) |
| Architecture and technology choices | [§6](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#6-arsitektur-teknis-dan-keputusan-teknologi) |
| Scenario data, time, geometry, and simulator | [§7](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#7-data-waktu-geometri-dan-simulator) |
| Clearances, roles, communication, or authority | [§8](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#8-clearance-komunikasi-dan-kewenangan) |
| Occupancy prediction, conflict rules, evidence, or alert lifecycle | [§9](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#9-prediksi-occupancy-dan-perhitungan-risiko), [§10](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#10-rule-severity-dan-evidence-alert) |
| Workload/complexity indicator | [§11](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#11-indikator-kompleksitas-tugas-dan-workload) |
| Dashboard, API, authentication, or synchronization | [§12](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#12-dashboard-dan-interaksi-pengguna), [§13](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#13-api-sinkronisasi-dan-akses) |
| Persistence, replay, branching, or reports | [§14](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#14-penyimpanan-replay-branching-dan-laporan) |
| Scenario fixtures, test strategy, or acceptance criteria | [§15](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#15-paket-skenario-dan-desain-benchmark), [§16](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#16-pengujian-dan-kriteria-penerimaan) |
| Human evaluation or future roadmap | [§17](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#17-evaluasi-training-dan-protokol-studi), [§18](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#18-backlog-tim-jadwal-dan-dependensi), [§19](Knowledge-Review/ATC_FlowLens_Rencana_Teknis_MVP.md#19-risiko-batasan-dan-jalur-setelah-mvp) |

For current behavior, also inspect the corresponding files in `backend/` or `frontend/`. For claims about real-world systems, consult the evidence register, not a pitch deck.

## Artifact policy

Markdown is the editable text source. Existing PDFs and pitch decks are retained as snapshots and may not match later Markdown edits; do not regenerate or treat them as current specifications unless a task explicitly asks for updated presentation exports. Do not treat simulated values, draft language, or visual examples as operational data or validation results.
