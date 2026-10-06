from __future__ import annotations

import hashlib
import json
import socket
import sys
import urllib.request
import zipfile
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import package_offline  # noqa: E402


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _mock_repository(root: Path) -> Path:
    files = {
        "pyproject.toml": '[project]\nname="fixture-app"\nversion="0.1.0"\ndependencies=[]\n',
        "backend/__init__.py": "",
        "backend/app.py": "# mock package source\n",
        "backend/detection.py": "# mock package source\n",
        "backend/models.py": 'ENGINE_VERSION = "fixture-1"\nCONFIG_VERSION = "fixture-config-1"\n',
        "backend/reporting.py": "# mock package source\n",
        "backend/review.py": "# mock package source\n",
        "backend/scenarios.py": 'LAYOUT = {"id": "fixture-layout", "version": "1.0"}\n',
        "backend/session.py": "# mock package source\n",
        "backend/simulator.py": "# mock package source\n",
        "backend/storage.py": "# mock package source\n",
        "backend/data/scenarios.json": json.dumps([{"id": f"S{i:02d}"} for i in range(1, 13)]),
        "frontend/package.json": '{"name":"fixture-ui","version":"0.1.0"}',
        "frontend/package-lock.json": '{"name":"fixture-ui","lockfileVersion":3}',
        "frontend/dist/index.html": "<html><body>fixture</body></html>",
        "frontend/dist/assets/app.js": "console.log('fixture');",
        "tests/fixtures/replay/benchmark-manifest.json": '{"label":"FIXTURE/MOCK"}',
    }
    for relative, content in files.items():
        _write(root / relative, content)

    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir(parents=True)
    wheel_path = wheelhouse / "demo_runtime-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as wheel:
        wheel.writestr(
            "demo_runtime-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: demo-runtime\nVersion: 1.0\n",
        )
    wheel_hash = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
    _write(root / "requirements.lock", f"demo-runtime==1.0 --hash=sha256:{wheel_hash}\n")

    # These local assets are deliberate negative inputs. The package allowlist must ignore them.
    _write(root / "runtime/operator-key.txt", "throwaway-operator-token-do-not-package")
    _write(root / "tests/fixtures/private/truth.json", '{"truth":"restricted"}')
    _write(root / "restricted/export.csv", "restricted export")
    _write(root / "runtime/private-audio/sample.wav", b"audio")
    _write(root / ".env", "FLOWLENS_OPERATOR_KEY=do-not-package")
    return wheel_path


def test_package_manifest_hashes_only_allowlisted_mock_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repository"
    _mock_repository(root)

    def network_forbidden(*args, **kwargs):
        raise AssertionError("offline package assembly must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", network_forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", network_forbidden)

    output = root / "tmp" / "offline-package"
    manifest = package_offline.build_package(root, output)

    assert output.is_dir()
    assert manifest["label"].startswith("FIXTURE/MOCK")
    assert manifest["ai"]["status"] == "unavailable"
    assert manifest["source_replay"]["status"] == "unavailable"
    assert manifest["dependencies"]["python_wheels_included"] == 1
    assert manifest["security"]["credentials_included"] is False
    assert manifest["security"]["private_truth_included"] is False
    assert manifest["security"]["restricted_exports_included"] is False
    assert manifest["security"]["audio_included"] is False
    assert manifest["cold_runtime"]["status"] == "not_run"

    for artifact in manifest["artifacts"]:
        packaged = output / artifact["path"]
        assert packaged.is_file()
        assert packaged.stat().st_size == artifact["size_bytes"]
        assert hashlib.sha256(packaged.read_bytes()).hexdigest() == artifact["sha256"]
        assert not package_offline._is_sensitive(artifact["path"])

    included = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    assert "wheelhouse/demo_runtime-1.0-py3-none-any.whl" in included
    assert "frontend/dist/assets/app.js" in included
    assert "runtime/operator-key.txt" not in included
    assert "tests/fixtures/private/truth.json" not in included
    assert "restricted/export.csv" not in included
    assert "runtime/private-audio/sample.wav" not in included
    assert ".env" not in included
    assert "runtime/operator-key.txt" not in {row["path"] for row in manifest["artifacts"]}


def test_missing_required_package_inputs_fail_explicitly_without_output(tmp_path: Path) -> None:
    root = tmp_path / "empty-repository"
    root.mkdir()
    output = root / "tmp" / "offline-package"

    with pytest.raises(package_offline.PackagePreflightError) as captured:
        package_offline.build_package(root, output)

    details = "\n".join(captured.value.problems)
    assert "pyproject.toml" in details
    assert "requirements.lock" in details
    assert "frontend/dist/index.html" in details
    assert "wheelhouse/" in details
    assert not output.exists()


def test_existing_output_is_preserved(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _mock_repository(root)
    output = root / "tmp" / "offline-package"
    output.mkdir(parents=True)
    marker = output / "keep.txt"
    marker.write_text("existing local artifact", encoding="utf-8")

    with pytest.raises(package_offline.PackagePreflightError, match="refusing to overwrite"):
        package_offline.build_package(root, output)

    assert marker.read_text(encoding="utf-8") == "existing local artifact"
