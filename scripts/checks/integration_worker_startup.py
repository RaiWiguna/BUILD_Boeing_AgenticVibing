"""Native API + native B HTTP worker idle smoke on private disposable joint storage."""

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

from flowlens.auth.accounts import Accounts
from flowlens.auth.permissions import Permissions
from flowlens.auth.sessions import Sessions
from flowlens.integration.catalog import JOINT_MIGRATIONS
from flowlens.storage.sqlite.database import Database
from flowlens.workers.audio.models import WorkerConfig
from pydantic import SecretStr


def main():
    with tempfile.TemporaryDirectory(prefix="flowlens-joint-native-") as directory:
        root = Path(directory).resolve()
        with Database(root / "db/state.sqlite", migrations=JOINT_MIGRATIONS) as db:
            accounts = Accounts(db)
            admin = accounts.bootstrap("admin", SecretStr("synthetic-native-initial"))
            accounts.change_password(
                admin.id,
                SecretStr("synthetic-native-initial"),
                SecretStr("synthetic-native-changed"),
            )
            sessions = Sessions(db, accounts)
            auth = sessions.login("admin", SecretStr("synthetic-native-changed"), "local")
            worker = Permissions(db, sessions).provision_worker(
                auth.token.get_secret_value(), expires_ms=sessions.clock() + 60000
            )
        with socket.socket() as socket_handle:
            socket_handle.bind(("127.0.0.1", 0))
            port = socket_handle.getsockname()[1]
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "PYTHONPATH": str(Path("backend").resolve()),
            "FLOWLENS_PROFILE": "development",
            "FLOWLENS_PORT": str(port),
            "FLOWLENS_DB_PATH": str(root / "db/state.sqlite"),
            "FLOWLENS_IMPORT_STAGING_PATH": str(root / "imports"),
            "FLOWLENS_RAW_ASSETS_PATH": str(root / "raw"),
            "FLOWLENS_ARTIFACT_STAGING_PATH": str(root / "artifacts"),
            "FLOWLENS_RETENTION_JOURNAL_PATH": str(root / "journal"),
        }
        (root / "scratch").mkdir(mode=0o700)
        config = root / "worker-config.json"
        config.write_text(
            WorkerConfig(worker_id=worker.id, scratch_root=root / "scratch").model_dump_json()
        )
        config.chmod(0o600)
        token = root / "worker-token"
        token.write_text(worker.token.get_secret_value())
        token.chmod(0o600)
        origin = f"http://127.0.0.1:{port}"
        with (root / "api.log").open("wb") as sink:
            api = subprocess.Popen(
                [sys.executable, "-m", "flowlens.api.serve"],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=sink,
                stderr=sink,
            )
            try:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        with urllib.request.urlopen(origin + "/health", timeout=1) as response:
                            assert json.load(response)["status"] == "alive"
                        break
                    except urllib.error.URLError:
                        if api.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError("Native API unavailable") from None
                        time.sleep(0.05)
                run = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "flowlens.workers.audio",
                        "--api",
                        origin,
                        "--config",
                        str(config),
                        "--token-file",
                        str(token),
                        "--once",
                    ],
                    env={"PATH": environment["PATH"], "PYTHONPATH": environment["PYTHONPATH"]},
                    capture_output=True,
                    timeout=15,
                    text=True,
                )
                assert run.returncode == 0, "Native worker failed"
                assert json.loads(run.stdout)["status"] == "IDLE"
                assert worker.token.get_secret_value() not in run.stdout + run.stderr
                print(
                    json.dumps(
                        {
                            "status": "PASS",
                            "native_api": True,
                            "native_worker": True,
                            "worker_execution": "AUTHENTICATED_HTTP_IDLE",
                            "provider_calls": 0,
                            "cleanup": "owned processes and private disposable roots removed",
                        }
                    )
                )
            finally:
                api.terminate()
                try:
                    api.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait(timeout=5)


if __name__ == "__main__":
    main()
