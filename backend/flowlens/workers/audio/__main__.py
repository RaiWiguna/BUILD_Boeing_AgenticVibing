"""Native isolated audio executor over authenticated HTTP; no SQLite or cloud calls."""

import argparse
import json
import os
import signal
import stat
import threading
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from flowlens.audio import AudioError, AudioTools
from flowlens.workers.audio.http import AudioPorts
from flowlens.workers.audio.models import WorkerConfig
from flowlens.workers.audio.worker import AudioWorker


def private_bytes(path: Path, limit: int) -> bytes:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Private file required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        facts = os.fstat(descriptor)
        if (
            not stat.S_ISREG(facts.st_mode)
            or facts.st_nlink != 1
            or facts.st_uid != os.geteuid()
            or facts.st_mode & 0o077
            or facts.st_size > limit
        ):
            raise ValueError("Private file required")
        return os.read(descriptor, limit + 1)
    finally:
        os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    try:
        url = urlsplit(args.api)
        if (
            url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
            or url.scheme not in ("http", "https")
        ):
            raise ValueError("API origin required")
        if (
            url.scheme == "http"
            and url.hostname != "localhost"
            and not ip_address(url.hostname or "").is_loopback
        ):
            raise ValueError("TLS required")
        config = WorkerConfig.model_validate_json(private_bytes(args.config, 65536))
        token = private_bytes(args.token_file, 1024).decode().strip()
        if not token.startswith("wrk_") or not 20 <= len(token) <= 256:
            raise ValueError("Worker token required")
        stop = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.set())
        with httpx.Client(
            base_url=args.api,
            timeout=min(config.heartbeat_seconds, 1.0),
            trust_env=False,
            follow_redirects=False,
        ) as client:
            ports = AudioPorts(client, token)
            worker = AudioWorker(config, ports, ports, ports, AudioTools.discover(), shutdown=stop)
            outcome = worker.run_once() if args.once else worker.serve()
        print(
            json.dumps(
                {
                    "status": outcome.status,
                    "code": outcome.code,
                    "profile": "LOCAL_AUDIO_NO_CLOUD",
                    "provider_verified": False,
                }
            )
        )
        raise SystemExit(0 if outcome.status in ("IDLE", "RECEIPT") else 1)
    except (ValueError, OSError, AudioError, httpx.HTTPError):
        print(
            json.dumps({"status": "BLOCKED", "code": "WORKER_CONFIGURATION_OR_TRANSPORT_INVALID"})
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
