"""Private staging leases permit safe cleanup after a process crash, never active work."""

import fcntl
import json
import os
import re
import shutil
from pathlib import Path

from flowlens.assets.storage import PrivateFiles
from flowlens.imports.inspection import strict_json

PATTERN = (
    r"\.(?:snapshot|restore)-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.tmp"
)


def reserve(stage: Path) -> int:
    descriptor = os.open(
        str(stage) + ".lease", os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        PrivateFiles.private(descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        body = json.dumps({"version": "maintenance-stage-1", "candidate": stage.name}).encode()
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(body)
            stream.flush()
            os.fsync(descriptor)
        sync(stage.parent)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def release(stage: Path, descriptor: int) -> None:
    try:
        os.unlink(str(stage) + ".lease")
        sync(stage.parent)
    finally:
        os.close(descriptor)


def sync(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sync_tree(root: Path) -> None:
    for folder, _, _ in root.walk(top_down=False, follow_symlinks=False):
        sync(folder)


def cleanup(parent: Path) -> dict[str, int]:
    if any(p.is_symlink() for p in (parent, *parent.parents)):
        raise ValueError("Private candidate parent required")
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    removed = active = 0
    try:
        PrivateFiles.private(directory, directory=True)
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".lease") or re.fullmatch(PATTERN, name[:-6]) is None:
                continue
            descriptor = os.open(name, os.O_RDWR | os.O_NOFOLLOW, dir_fd=directory)
            try:
                PrivateFiles.private(descriptor)
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    active += 1
                    continue
                data = strict_json(os.read(descriptor, 4097).decode())
                if data != {"version": "maintenance-stage-1", "candidate": name[:-6]}:
                    raise ValueError("Unknown candidate lease")
                stage = parent / name[:-6]
                if stage.exists() or stage.is_symlink():
                    if stage.is_symlink():
                        raise ValueError("Invalid candidate directory")
                    candidate = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                    try:
                        PrivateFiles.private(candidate, directory=True)
                    finally:
                        os.close(candidate)
                    shutil.rmtree(stage)
                os.unlink(name, dir_fd=directory)
                os.fsync(directory)
                removed += 1
            finally:
                os.close(descriptor)
    finally:
        os.close(directory)
    return {"removed_candidates": removed, "active_candidates": active}
