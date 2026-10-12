"""Registry of prepared demo scenarios (data/demo-scenarios/<id>/scenario.json).

A scenario has recordings ("parts"): one main part and optional parts recorded before or
after it, each with an audio file and an optional ADS-B CSV. Uploaded files are matched by
name, then by SHA-256 and size. The accepted file set selects one prepared analysis
("variant"); the server always uses its own canonical copy of the assets.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROLES = ("audio", "adsb")
POSITIONS = ("before", "main", "after")


def variant_key(files: Iterable[tuple[str, str]]) -> str:
    """Stable key for a set of (part, role) pairs, e.g. '87:audio,88:adsb,88:audio'."""
    return ",".join(sorted(f"{part}:{role}" for part, role in set(files)))


@dataclass(frozen=True)
class FileRef:
    part: str
    role: str
    meta: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.meta["name"])


@dataclass(frozen=True)
class Scenario:
    id: str
    root: Path
    data: dict[str, Any]

    @property
    def parts(self) -> dict[str, dict[str, Any]]:
        return self.data["parts"]  # type: ignore[no-any-return]

    @property
    def main_part(self) -> str:
        return str(self.data["main_part"])

    def position(self, part: str) -> str:
        return str(self.parts[part]["position"])

    def file(self, name: str) -> FileRef | None:
        for part, meta in self.parts.items():
            for role in ROLES:
                if meta.get(role, {}).get("name") == name:
                    return FileRef(part, role, meta[role])
        return None

    def variant(self, files: Iterable[tuple[str, str]]) -> dict[str, Any] | None:
        return self.data["variants"].get(variant_key(files))  # type: ignore[no-any-return]

    def audio_path(self, part: str) -> Path:
        return self.root / str(self.parts[part]["audio"]["derived"]["path"])

    def expected(self) -> list[dict[str, str]]:
        return [
            {"name": meta[role]["name"], "role": role, "position": meta["position"], "part": part}
            for part, meta in self.parts.items()
            for role in ROLES
            if role in meta
        ]


class Registry:
    def __init__(self, root: Path):
        self.root = root
        self._by_id: dict[str, Scenario] = {}
        self.reload()

    def reload(self) -> None:
        self._by_id.clear()
        if not self.root.is_dir():
            return
        for path in sorted(self.root.glob("*/scenario.json")):
            raw = path.read_bytes()
            data = json.loads(raw)
            if data.get("version") != 2:
                continue
            # Stored analyses built from another revision of this file are rebuilt on read.
            data["build"] = hashlib.sha256(raw).hexdigest()[:16]
            self._by_id[data["scenario_id"]] = Scenario(data["scenario_id"], path.parent, data)

    def get(self, scenario_id: str) -> Scenario | None:
        return self._by_id.get(scenario_id)

    def by_file_name(self, name: str) -> tuple[Scenario, FileRef] | None:
        for sc in self._by_id.values():
            ref = sc.file(name)
            if ref:
                return sc, ref
        return None

    def expected(self) -> list[dict[str, str]]:
        return [f for sc in self._by_id.values() for f in sc.expected()]

    def __len__(self) -> int:
        return len(self._by_id)
