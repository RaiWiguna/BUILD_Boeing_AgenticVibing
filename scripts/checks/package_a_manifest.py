"""Generate/check the actual A host inventory without provider calls or private data."""

import argparse
import ast
import hashlib
import inspect
import json
import subprocess
import tempfile
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import get_args

from flowlens import CONTRACT_VERSION
from flowlens.api.host import create_host, route_keys
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration
from flowlens.geometry.kernel import GEOMETRY_VERSION
from flowlens.geometry.rules import RuleProfile
from flowlens.imports.staging import ImportLimits
from flowlens.jobs.coordinator import Stage, StagePolicy
from flowlens.replay.snapshots import REDUCER_VERSION
from flowlens.storage.sqlite.database import Database
from flowlens.storage.sqlite.migrate import checksum
from flowlens.storage.sqlite.repository import KINDS
from flowlens.storage.sqlite.schema import PLATFORM_MIGRATIONS

TARGET = Path("docs/development/package-a-manifest.json")


def generate(acceptance_sha):
    subprocess.check_call(["git", "cat-file", "-e", acceptance_sha + "^{commit}"])
    tree = ast.parse(Path("backend/flowlens/core/host_config.py").read_text())
    mapping = next(
        ast.literal_eval(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "fields" for t in node.targets)
    )
    ports = ast.parse(Path("backend/flowlens/contracts/ports.py").read_text())
    lock = tomllib.loads(Path("uv.lock").read_text())
    project = tomllib.loads(Path("pyproject.toml").read_text())
    source_paths = sorted(
        [*Path("backend/flowlens").rglob("*.py"), *Path("contracts").rglob("*.json")]
        + [Path("pyproject.toml"), Path("uv.lock")]
    )
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    app = create_host(HostSettings(profile="test"))
    routes = sorted({key for route in app.routes for key in route_keys(route)})
    assert set(app.openapi()["paths"]) <= {p for p, _ in routes}
    with tempfile.TemporaryDirectory(prefix="flowlens-manifest-") as directory:
        with Database(Path(directory) / "inventory.db") as db, db.begin() as uow:
            tables = [
                r[0]
                for r in uow.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            applied = dict(
                uow.connection.execute("SELECT id,checksum FROM platform_schema_migrations")
            )
    assert applied == {m.id: checksum(m) for m in PLATFORM_MIGRATIONS}
    return {
        "manifest_version": "package-a-handoff-1",
        "candidate": {
            "prerequisite_sha": "1f88f38971f1e171fd2421aa8647424e429e26f1",
            "acceptance_commit_sha": acceptance_sha,
            "handoff_commit_resolution": (
                "git log -1 --format=%H -- docs/development/package-a-manifest.json"
            ),
            "source_identity": (
                "exact source_sha256 map; handoff commit includes route inventory fix"
            ),
        },
        "versions": {
            "contracts": CONTRACT_VERSION,
            "reducer": REDUCER_VERSION,
            "geometry": GEOMETRY_VERSION,
            "rules": RuleProfile().version,
            "lab_layout": RuleProfile().layout_version,
            "python": project["project"]["requires-python"],
        },
        "source_sha256": hashes,
        "entrypoints": {
            "host": "python -m flowlens.api.serve",
            "composition": "flowlens.api.host:create_host",
            "bootstrap": "python -m flowlens.cli.bootstrap_admin",
            "legacy_archive": "python -m flowlens.cli.migrate_archive",
            "maintenance": "python -m flowlens.cli.maintenance",
            "contract_smoke": "python -m flowlens.testing --track A (MOCK only)",
        },
        "host_parameters": list(inspect.signature(create_host).parameters),
        "config_environment_to_field": mapping,
        "config_defaults": HostSettings().model_dump(mode="json"),
        "import_limits": ImportLimits().model_dump(),
        "dependencies": {
            "declared_runtime": project["project"]["dependencies"],
            "locked_packages": {p["name"]: p.get("version", "local") for p in lock["package"]},
            "provider_sdks": "google-cloud-speech/google-genai adapters not implemented by A",
        },
        "routes": [{"path": p, "method": m} for p, m in routes],
        "migrations": [
            {
                "id": m.id,
                "owner": m.owner,
                "depends_on": list(m.depends_on),
                "checksum": checksum(m),
            }
            for m in PLATFORM_MIGRATIONS
        ],
        "tables": tables,
        "repository_namespaces": {k: [c.__name__ for c in v] for k, v in KINDS.items()},
        "frozen_ports": {
            node.name: [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            for node in ports.body
            if isinstance(node, ast.ClassDef)
        },
        "module_registration_fields": [f.name for f in fields(ModuleRegistration)],
        "stage_policy_fields": [f.name for f in fields(StagePolicy)],
        "supported_job_stages": list(get_args(Stage)),
        "actual_registrations": {
            "default_analysis_module": None,
            "default_job_policies": [],
            "default_B_routes_migrations_repositories": [],
            "default_snapshot_reader": None,
            "default_B_purge_callbacks": [],
            "acceptance_fake": (
                "test-only frozen fake snapshot/AnalysisModule; no production fallback"
            ),
            "jobs": (
                "explicit analysis_module + StagePolicy + repository_factories; "
                "not automatic from ModuleRegistration.job_handlers"
            ),
            "snapshot": (
                "one module.snapshot_reader OR AnalysisModule.snapshot; duplicates rejected"
            ),
            "purge": (
                "module.inventory_namespaces required; callback mapped by first "
                "namespace; unknown inventory fails closed"
            ),
            "maintenance": (
                "standalone CLI only A migrations; integrated B maintenance "
                "composition/reconciliation required in Phase10"
            ),
        },
        "sensitive_inventory": {
            "sqlite": (
                "accounts/password hashes, cookie and worker token hashes, "
                "grants, revisions, source metadata/rights, evidence quotes, "
                "jobs/results/usage, audit/receipts, replay caches"
            ),
            "raw_assets": (
                "immutable uploaded audio and observed sidecars under opaque private storage keys"
            ),
            "import_staging": (
                "untrusted uploads plus draft metadata/rights/retention; TTL24h and bounded counts"
            ),
            "artifact_staging": (
                "pending/accepted derivative audio and reports; current "
                "permission/hash/expiry required"
            ),
            "tombstone_journal": (
                "current ledger.jsonl/head.json outside restored roots; minimal deletion authority"
            ),
            "backup": (
                "LOCAL_PRIVATE_UNENCRYPTED snapshot includes sensitive DB/assets; "
                "retention prune required"
            ),
            "logs": (
                "IDs/status/timing/hashes/usage only; no transcript/audio/key/header/provider body"
            ),
            "B_inventory": (
                "must declare analysis.* records, "
                "transcript/memory/findings/options/reviews/briefs/query/report/provider "
                "scratch and purge behavior at integration"
            ),
        },
        "commands_results": {
            "record": "docs/testing/a101-evidence.md",
            "manifest_check": ".venv/bin/python scripts/checks/package_a_manifest.py --check",
            "final_audit": "docs/testing/a10-completion-audit.md",
        },
        "measured_baseline": {
            "record": "docs/testing/a101-benchmark.json",
            "final_reconfirmation": "docs/testing/a102-benchmark.json",
            "profile": (
                "100 sessions,20objects,60min replay,60s track cadence,two60min audio channels"
            ),
            "timing_transport": "ASGI local; excludes browser/LAN/provider",
        },
        "status": {
            "A_source": "available",
            "A_tests_build": "passed; see command evidence",
            "A_platform_benchmark": "measured; declared profile only",
            "B_composition": "not_started",
            "provider_verified": False,
            "domain": "NOT_DOMAIN_VALIDATED",
            "operational": "not_validated",
            "G_BE": "not_started",
            "Phase10": "planned",
        },
        "remaining_limitations": [
            "No real B/provider smoke/semantic held-out evaluation or approved partner source",
            "No browser/VM/high-frequency throughput benchmark; p95 snapshot has narrow margin",
            "No frontend/container/deployment/off-host encrypted backup or scheduler",
            (
                "Maintenance CLI rejects non-A migration ledger; B-aware "
                "composition must be reconciled"
            ),
            (
                "ModuleRegistration.services/repositories/job_handlers/readiness/config_keys "
                "are descriptors; host parameters/policies/adapters require explicit wiring"
            ),
            (
                "Locked FastAPI lazy include route traversal uses its "
                "effective_candidates; retest on dependency updates"
            ),
            (
                "Purge inventory declarations describe analysis.* namespaces, not "
                "arbitrary SQL tables; custom B table/restore compatibility must be proved "
                "at integration"
            ),
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance-sha")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sha = args.acceptance_sha
    if args.check and sha is None:
        sha = json.loads(TARGET.read_text())["candidate"]["acceptance_commit_sha"]
    if sha is None:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    value = generate(sha)
    if args.check:
        if json.loads(TARGET.read_text()) != value:
            raise SystemExit("Package A manifest drift; regenerate and review source inventory")
        print("Package A manifest/source/config/migrations/routes/dependencies match")
    else:
        TARGET.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        print(
            f"Saved {TARGET}: {len(value['routes'])} route/methods, "
            f"{len(value['migrations'])} migrations"
        )


if __name__ == "__main__":
    main()
