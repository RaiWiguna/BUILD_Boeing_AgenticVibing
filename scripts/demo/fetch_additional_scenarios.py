"""Copy exactly five existing research WAVs through SSH and verify immutable hashes.

Usage: VM=user@host SSH_KEY=/private/key python3 scripts/demo/fetch_additional_scenarios.py
Requires the ignored research candidate manifest; never requests a provider or changes 87/88.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARTS = (50, 51, 47, 156, 123)


def main():
    vm, key = os.environ.get("VM"), os.environ.get("SSH_KEY")
    if not vm or not key:
        raise SystemExit("Set VM and SSH_KEY in the environment (not source files).")
    if not re.fullmatch(r"[A-Za-z0-9_.@:-]+", vm):
        raise SystemExit("Invalid SSH target")
    candidates = json.loads(
        (ROOT / "outputs/tartan-research/mock-case-candidates.json").read_text()
    )
    for part in PARTS:
        f = candidates[f"{part}.wav"]
        if not re.fullmatch(
            r"/home/deploy/flowlens-research/tartan/[A-Za-z0-9_./-]+", f["path"]
        ):
            raise SystemExit("Unexpected research source path")
        date = "2022-09-11" if part == 156 else "2022-09-10"
        folder = ROOT / f"data/demo-scenarios/kagc-{date}-{part}"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{part}.wav"
        if not target.exists():
            subprocess.run(
                [
                    "scp",
                    "-q",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "IdentitiesOnly=yes",
                    "-i",
                    key,
                    vm + ":" + f["path"],
                    str(target),
                ],
                check=True,
            )
        if hashlib.sha256(target.read_bytes()).hexdigest() != f["sha256"]:
            raise SystemExit(f"{part}: checksum mismatch; source not overwritten")
        target.chmod(0o600)
        (folder / f"{part}.txt").write_text(f["metadata"])
        print(f"{part}: immutable source verified")


if __name__ == "__main__":
    main()
