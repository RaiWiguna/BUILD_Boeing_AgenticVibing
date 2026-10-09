"""Known-signature scan of complete tracked/staged files; never print matched bytes.

This deliberately bounded fallback is not entropy/history scanning or certification.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

SIGNATURES = {
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "google_key": rb"AIza[0-9A-Za-z_-]{35}",
    "aws_access_key": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "github_token": rb"(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})",
    "slack_token": rb"xox[baprs]-[0-9A-Za-z-]{20,}",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    if args.staged:
        paths = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
        ).split(b"\0")
    findings = []
    scanned = 0
    for raw in paths:
        if not raw:
            continue
        path = raw.decode()
        body = (
            subprocess.check_output(["git", "show", ":" + path])
            if args.staged
            else Path(path).read_bytes()
        )
        scanned += 1
        for kind, pattern in SIGNATURES.items():
            if re.search(pattern, body):
                findings.append({"file": path, "kind": kind})
    result = {
        "scope": "complete staged files" if args.staged else "complete tracked files",
        "files": scanned,
        "findings": findings,
        "limits": "known PEM/Google/AWS/GitHub/Slack signatures only; no entropy/history scan",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
