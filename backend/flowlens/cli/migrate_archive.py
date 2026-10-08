"""Explicit local maintenance command; never reads or migrates old credentials."""

import argparse
import json
from pathlib import Path

from flowlens.storage.sqlite.database import Database
from flowlens.storage.sqlite.legacy import import_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert supported historical replay archive")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not args.source.is_file() or args.source.resolve() == args.target.resolve():
            raise ValueError("Separate source and target required.")
        with Database(args.target) as target:
            result = import_archive(args.source, target)
    except Exception:
        raise SystemExit(
            "Archive conversion failed; check schema, IDs and file ownership."
        ) from None
    print(json.dumps({"profile": result.profile, "digest": result.digest, "counts": result.counts}))


if __name__ == "__main__":
    main()
