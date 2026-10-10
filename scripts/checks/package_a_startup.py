"""Exercise the documented A launcher on disposable private roots/native loopback."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-ready", type=int, choices=(200, 503), default=503)
    expected_ready = parser.parse_args().expected_ready
    with tempfile.TemporaryDirectory(prefix="flowlens-startup-") as directory:
        root = Path(directory).resolve()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        environment = {
            "PATH": os.defpath,
            "FLOWLENS_PROFILE": "development",
            "FLOWLENS_PORT": str(port),
            "FLOWLENS_DB_PATH": str(root / "db" / "data.db"),
            "FLOWLENS_IMPORT_STAGING_PATH": str(root / "imports"),
            "FLOWLENS_RAW_ASSETS_PATH": str(root / "raw"),
            "FLOWLENS_ARTIFACT_STAGING_PATH": str(root / "artifacts"),
            "FLOWLENS_RETENTION_JOURNAL_PATH": str(root / "journal"),
        }
        with (root / "launcher.log").open("wb") as output:
            process = subprocess.Popen(
                [sys.executable, "-m", "flowlens.api.serve"],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=output,
            )
            try:
                url = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 15
                while True:
                    try:
                        with urllib.request.urlopen(url + "/health", timeout=1) as response:
                            assert json.load(response)["status"] == "alive"
                        break
                    except urllib.error.URLError:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            Path("artifacts/reports/a102-launcher-failure.log").write_bytes(
                                (root / "launcher.log").read_bytes()
                            )
                            raise RuntimeError("Documented startup failed") from None
                        time.sleep(0.05)
                with urllib.request.urlopen(url + "/release.json", timeout=2) as response:
                    release = json.load(response)
                    assert release["provider_verified"] is False
                with urllib.request.urlopen(url + "/openapi.json", timeout=2) as response:
                    schema = json.load(response)
                    assert "/api/v1/sessions" in schema["paths"]
                for path, status in [("/ready", expected_ready), ("/api/v1/sessions", 401)]:
                    try:
                        response = urllib.request.urlopen(url + path, timeout=2)
                    except urllib.error.HTTPError as error:
                        assert error.code == status
                    else:
                        assert response.status == status
                        response.close()
                print(
                    json.dumps(
                        {
                            "health": 200,
                            "release": 200,
                            "openapi": 200,
                            "ready": expected_ready,
                            "unauthenticated_catalogue": 401,
                            "profile": "development",
                            "provider_verified": False,
                            "cleanup": "owned process terminated and temporary roots removed",
                        }
                    )
                )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
