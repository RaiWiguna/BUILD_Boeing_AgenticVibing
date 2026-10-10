"""Materialize or verify the local composition catalog against actual source."""

import argparse
import hashlib
import json
from pathlib import Path

from flowlens.core.host_config import HostSettings
from flowlens.core.modules import order_migrations
from flowlens.integration import create_integrated_host
from flowlens.integration.catalog import JOINT_MIGRATIONS, TABLES, repositories
from flowlens.integration.engine import CONFIG
from flowlens.storage.sqlite.migrate import checksum


def inventory():
    app = create_integrated_host(HostSettings(profile="test"))
    paths = sorted(Path("backend/flowlens").rglob("*.py")) + [
        Path("pyproject.toml"),
        Path("uv.lock"),
        Path("scripts/checks/package_a_startup.py"),
        Path("scripts/checks/integration_manifest.py"),
        Path("scripts/checks/integration_worker_startup.py"),
        Path("tests/platform/test_integration.py"),
    ]
    return {
        "input_sha": "3917b1614be90e990419ab85edbef1d74e6bc155",
        "candidate": "git log -1 --format=%H -- docs/development/backend-integration.json",
        "contract_version": "1.0.0",
        "composition": "LOCAL_A_B_NORMALIZED_PIPELINE",
        "providers": "NOT_CONFIGURED",
        "provider_calls": 0,
        "G_BE": "not_started",
        "domain": "NOT_DOMAIN_VALIDATED",
        "sources": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "migrations": [
            {
                "id": s.id,
                "owner": s.owner,
                "depends_on": list(s.depends_on),
                "checksum": checksum(s),
            }
            for s in order_migrations(list(JOINT_MIGRATIONS))
        ],
        "repositories": sorted(repositories()),
        "sensitive_tables": list(TABLES),
        "routes": sorted(
            method.upper() + " " + path
            for path, operations in app.openapi()["paths"].items()
            for method in operations
            if method in {"get", "post", "put", "delete", "patch"}
        ),
        "test_analysis_config": CONFIG.model_dump(mode="json"),
        "snapshot": "AnalysisModule.snapshot -> Engine.snapshot -> B reconstruct/assemble",
        "purge": "Engine.purge callback + exact session erasure TABLES in A Retention",
        "entrypoints": [
            "flowlens.api.serve",
            "flowlens.workers.audio",
            "flowlens.cli.bootstrap_admin --integrated",
            "flowlens.cli.maintenance",
        ],
        "sensitive_inventory": {
            "analysis_transcript": (
                "raw/words/normalized/corrections scoped tables; raw SDK route deferred"
            ),
            "analysis_intent_submissions": "private candidate/quote/provenance per attempt",
            "analysis_memory_ledger": "accepted intent/association/invalidation metadata/evidence",
            "analysis_advisory_ledger": "document/review/note metadata, factual text/evidence",
            "analysis_public_records": "frozen transcript/intent/finding/brief projections",
            "artifacts": "private audio chunks/frame/clock/hash provenance; no credential",
        },
        "limitations_document": "docs/development/backend-integration.md",
        "evidence_document": "docs/testing/integration-local-evidence.md",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = Path("docs/development/backend-integration.json")
    actual = inventory()
    if args.write:
        path.write_text(json.dumps(actual, indent=2) + "\n")
    else:
        assert json.loads(path.read_text()) == actual, "Integration manifest drift"
    print(
        json.dumps(
            {
                "status": "PASS",
                "migrations": len(actual["migrations"]),
                "sources": len(actual["sources"]),
                "routes": len(actual["routes"]),
            }
        )
    )


if __name__ == "__main__":
    main()
