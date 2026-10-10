# Objective audit — A01–A06 prerequisites, A07.1–A09.3

9 Oktober 2026, feat/backend-aben. Audit terhadap source/tests/Git, bukan status roadmap saja. Entry clean21457f3; final A09.3 commit adalah commit yang membawa dokumen ini (`git log -1` pada candidate). Commit sebelumnya diverifikasi lewat actual ancestry/log. Tidak ada push/merge/amend/destructive Git/B/frontend/deployment/Phase10/A10 execution.

## Prerequisites verified

Entry checks:425 platform,66 contracts tiap track A/B, Ruff63/mypy44/drift/Bandit/build PASS. Current full platform suite menguji kembali foundation bersama perubahan recovery.

| Unit | Actual source di backend/flowlens | Actual test_platform module / evidence |
| --- | --- | --- |
| A01 | api/host, core/host_config, storage/sqlite/{database,schema,migrate,legacy}, cli/migrate_archive | test_host, test_persistence, test_legacy; [A01.1](a011-evidence.md), [A01.2](a012-evidence.md), [A01.3](a013-evidence.md) |
| A02 | auth/{accounts,sessions}, auth/routes dan cli account lifecycle | test_accounts, test_sessions; [A02.1](a021-evidence.md), [A02.2](a022-evidence.md) |
| A03 | auth/permissions, auth/transport, api/serializers, storage/sqlite/mutations | test_permissions, test_transport, test_mutations; [A03.1](a031-evidence.md), [A03.2](a032-evidence.md), [A03.3](a033-evidence.md) |
| A04 | imports/{staging,metadata,commit}, clocks/normalization, sources/store | test_imports, test_import_metadata, test_import_commit; [A04](a04-evidence.md) |
| A05 | assets/{storage,access}, evidence registry | test_assets_evidence; [A05](a05-evidence.md) |
| A06 | jobs coordinator/lease/result/policy | test_jobs: race/atomic rollback/authority/revocation/actual process crash/reopen/schema upgrade; [A06](a06-evidence.md) |

Accounts/grants are real platform authorization, source data synthetic. Completed A06 ancestry7328ae8 and handoff21457f3 present; no uncommitted prerequisite changes were replaced.

## Sequential completed units

| Unit | Local conventional commit | Requirement → actual source/test evidence | Unit full platform |
| --- | --- | --- | --- |
| A07.1 | 1d48791ab19c567aa88a6439b53e585bb0f30e1b | replay snapshots/reducer/checkpoints/hash/as-of; test_replay_snapshots; [evidence](a071-evidence.md) | 444 |
| A07.2 | 52a6954aca3ab1e20ea4effc9aab99701277e5ad | replay controls leader/follow/local/play/pause/speed/seek/step/archive disposition; test_replay_controls/compatibility; [evidence](a072-evidence.md) | 466 |
| A07.3 | 8941ef904f4ac6d3fdff60a5355333d81b1d0137 | REST and frozen typed WS, revoke/reconnect/native bounded frames/resync; test_replay_transport; [evidence](a073-evidence.md) | 496 |
| A08.1 | c8c042299c152f0837e14119c48d587825b6ae56 | geometry kernel metric transforms/resources/hold/sweep; independent numeric oracle test_geometry_kernel; [evidence](a081-evidence.md) | 533 |
| A08.2 | ec63841f1d97b6c8c794d754ea63a95b36382388 | scoped occupancy/ETA/exit/margins/source eligibility/unknown; test_occupancy; [evidence](a082-evidence.md) | 566 |
| A08.3 | d263e085bd16ad34a984b65c1daafd948a574d75 | observed S01–S10 lab rules, independent math/time, source authority/alerts/seen/indicators; test_observed_rules/alert_reducer/rule_service/indicators/routes; [evidence](a083-evidence.md) | 620 |
| A09.1 | 22e72b331249858576c0fcebca27eb12ee2184b1 | artifacts promotion/download/expiry and retention/tombstones/inventory/audit; test_report_artifacts/retention/tombstones/artifact_retention_routes; [evidence](a091-evidence.md) | 657 |
| A09.2 | 9f9ee3e442819d45c742a247db94810d1a0f1c1b | ops health/release/logs/profiles/usage/disk; test_ops_health/profiles/usage_logs/routes; [evidence](a092-evidence.md) | 685 |
| A09.3 | This recovery commit, parent9f9ee3e | WAL-aware snapshot/assets/hash/grants/revisions/evidence/jobs/checkpoints/current retention/native crash/CLI/schema upgrade; test_recovery/cli/evidence/runs; [evidence](a093-evidence.md) | 712 |

Per-unit acceptance/checks/review/scans and handoff recorded in linked evidence, with scope/limitations; each unit has a local commit in dependency order. Earlier scan reports are ignored local artifacts, not committed secrets. Current frozen version1.0.0 schemas/ports/lock unchanged from A09.2; all17 previous migrations AST-identical, append0018 only. Earlier units appended13–17 and locked Shapely/wsproto changes as their evidence records describe.

## Final checks and boundaries

Final commands: `.venv/bin/pytest tests/platform -q`, contracts `--track A` and `--track B`, Ruff check/format backend/tests/scripts, mypy, contracts.generate --check, Bandit -ll, uv lock --check, uv build to ignored a093-dist, git diff --check. Recovery scoped27 PASS12.16s; both contracts66 PASS each; mypy78, Ruff120 formatted files; medium/high Bandit0 (existing2 LOW decoder findings/validated SQL exclusions remain). Full platform712 PASS (153.62s). No new dependency.

Available secret scan is staged-full-file PEM/Google/AWS/GitHub/Slack known signatures only,21 staged files/0 matches; dedicated gitleaks/trufflehog/git-secrets absent. Not entropy/history/full certification. Actual staged-file count/report at ignored artifacts/reports/a093-secret-scan.json. Markdown relative links/fences and staged whitespace checked. Source/diff reviewed before conventional commit; clean working tree and commit ancestry checked afterward.

Objective complete only after actual A09.3 commit and post-commit audit. Next **A10.1 only**. This audit does not execute A10 standalone capacity/performance/60-minute replay/100-session/20-object/two-channel two-hour acceptance. B/provider smoke/domain review/composition and production gates remain unperformed. Local readiness and private unencrypted recovery are platform capabilities; no operational certification. [Handoff](../../.agent/sessionHandoff.md).
