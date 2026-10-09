# A09.1 — artifact lifecycle, retention dan tombstones

Tanggal 9 Oktober 2026. Input commit `d263e085bd16ad34a984b65c1daafd948a574d75`; checkout `feat/backend-aben`, clean sebelum unit. Semua data berupa disposable synthetic fixture, real A SQLite/private filesystem/auth/jobs dan fake B frozen ports. Tidak ada partner corpus, provider call, renderer B, production purge atau persistent daemon.

## Source dan acceptance

- `artifacts/` implements frozen ArtifactLifecycle, code-owned report containers, accepted-only scoped metadata/inventory/download. Assets upload memeriksa active EXPORT attempt, creator/source permissions, private opaque paths/hash/size/container/expiry; atomic promotion tetap Jobs.result. JSON/CSV/HTML rendering/redaction/escaping milik B.
- `retention/` menyediakan admin preview yang bind contents/counts/packages, durable PREPARED/DONE plan (migration0016), cancellation/scope revocation, external chained minimal Tombstones, marker-before-erasure, retry, source expiry reconciliation, artifact expiry sweep dan bounded audit REST. Raw, derivative dan import-staging copies ikut dihapus. Old DB contents tidak mengalahkan current external marker.
- Human/worker reads memakai live deny-session guard; restored old/fresh context ditolak. Callback memakai frozen context/UOW signature dan registered analysis namespace; tidak dapat commit/rollback/nested-maintenance/after_commit atau mengubah global/other-session rows. Unknown namespace/custom SQL inventory gagal closed, bukan dianggap bersih.
- Startup reconciliation mendahului source-package verification. Journal private ownership, fsync chain/head, single writer dan corruption/truncation denial tested. No forensic/SSD/provider/backups instant-erasure claim; complete backup CLI A09.3 belum dikerjakan.

## Pemeriksaan

Final657 platform PASS (141.92s),37 scoped PASS (15.26s),66 contracts each track A/B PASS, Ruff100/mypy66/contract drift/Bandit -ll/uv lock/build PASS. Scoped tests mencakup three report formats/private-before-accept/promotion/download, expiry dan live grant revoke midstream, bad profile/capability/session/hash, truncated upload/orphan cleanup, rollback/retry; journal reopen/single owner/conflict/truncation; preview binding, marker/read denial, fault after marker/callback/files/before commit, idempotency, registered callbacks/authority/global isolation; old DB reconciliation/expiry; actual REST attachment/CSP/no-store/scope/CSRF/body/audit dan host reopen/cleanup.

Historical migration AST check membuktikan seluruh 15 existing definitions identik dengan input HEAD; hanya platform0016 appended. Frozen schema1.0.0 dan dependency lock unchanged. Static SQL identifier interpolations hanya dari schema yang lolos regex, values bound; four B608 exclusions scoped pada validated identifiers, termasuk hostile identifier/custom table test. Bandit two existing low decoder subprocess findings tetap tidak dinaikkan menjadi security certification.

Secret scan26 staged files/0 matches menggunakan available staged-file known-signature scan (PEM private keys, Google/AWS/GitHub/Slack token signatures); gitleaks/trufflehog/git-secrets tidak tersedia. Tidak ada entropy/history/full scanner claim. Ignored report disimpan dalam `artifacts/reports/a091-secret-scan.json`; runtime artifacts/test DB/private bytes tidak distage.

G-BE/G-FE/G-DELIVERY tetap not_started; `/ready` 503 HOST_ONLY. A09.1 final checks/review/scan/local commit diselesaikan pada milestone ini; A09.2 dan A09.3 masih berikutnya. Tidak ada push, merge, amend, frontend, Phase10 atau deployment.

Workflow/limits: [artifacts-retention](../development/artifacts-retention.md).
