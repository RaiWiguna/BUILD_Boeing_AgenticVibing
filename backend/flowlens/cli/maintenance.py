"""Offline local owner commands; new isolated destinations, sanitized output/errors."""

import argparse
import json
from pathlib import Path
from typing import NoReturn

from flowlens.recovery.candidates import cleanup
from flowlens.recovery.maintenance import Maintenance, Paths
from flowlens.recovery.snapshots import Snapshots


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError("Invalid maintenance arguments")


def main() -> None:
    parser = Parser(
        prog="flowlens-maintenance", description="Exclusive local maintenance; stop the API first"
    )
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
    for name in ("check", "backup"):
        sub = commands.add_parser(name)
        for key in ("database", "raw", "artifacts", "imports", "journal"):
            sub.add_argument("--" + key, type=Path, required=True)
        if name == "backup":
            sub.add_argument("--destination", type=Path, required=True)
    for name in ("verify", "restore", "prune"):
        sub = commands.add_parser(name)
        sub.add_argument("--backup", type=Path, required=True)
        sub.add_argument("--manifest-hash", required=True)
        if name in ("restore", "prune"):
            sub.add_argument("--journal", type=Path, required=True)
        if name == "restore":
            sub.add_argument("--target", type=Path, required=True)
    sub = commands.add_parser("cleanup")
    sub.add_argument("--parent", type=Path, required=True)
    try:
        args = parser.parse_args()
        if args.command in ("check", "backup"):
            paths = Paths(
                database=args.database,
                raw=args.raw,
                artifacts=args.artifacts,
                imports=args.imports,
                journal=args.journal,
            )
            with Maintenance(paths) as owner:
                output = (
                    owner.check()
                    if args.command == "check"
                    else Snapshots(owner).create(args.destination).model_dump(mode="json")
                )
        elif args.command == "verify":
            manifest = Snapshots.verify(args.backup, args.manifest_hash)
            output = {
                "status": "VERIFIED_LOCAL_SNAPSHOT",
                "id": str(manifest.id),
                "manifest_hash": args.manifest_hash,
                "files": len(manifest.files),
                "removal_due_ms": manifest.removal_due_ms,
            }
        elif args.command == "restore":
            restored = Snapshots.restore(
                args.backup,
                args.target,
                journal_path=args.journal,
                expected_manifest_hash=args.manifest_hash,
            )
            output = restored.model_dump(mode="json", exclude={"paths"})
        elif args.command == "cleanup":
            output = cleanup(args.parent)
        else:
            status = Snapshots.prune(
                args.backup, journal_path=args.journal, expected_manifest_hash=args.manifest_hash
            )
            output = {"status": status, "manifest_hash": args.manifest_hash}
    except Exception:
        raise SystemExit(
            "Maintenance failed; check ownership, initialized journal, supported schema, hashes, "
            "free disk and offline/new destination requirements."
        ) from None
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
