"""Owner-only deletion journal kept outside restored DB/assets. Corruption fails closed."""

import json
import os
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field

from flowlens.assets.storage import PrivateFiles
from flowlens.clocks.normalization import MetadataModel
from flowlens.core.errors import ContractError
from flowlens.imports.inspection import strict_json
from flowlens.imports.metadata import hashed


class Tombstone(MetadataModel):
    version: Literal["retention-journal-1"] = "retention-journal-1"
    session_id: UUID
    reason: Literal["USER_REQUEST", "RETENTION_EXPIRED"]
    inventory_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    deleted_ms: Annotated[int, Field(ge=0)]


class Tombstones:
    def __init__(self, path: Path) -> None:
        self.files = PrivateFiles(path)
        self.lock = RLock()
        try:
            names = os.listdir(self.files.fd)
            if "ledger.jsonl" not in names and "head.json" not in names:
                fd = os.open(
                    "ledger.jsonl",
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=self.files.fd,
                )
                os.fsync(fd)
                os.close(fd)
                self._head(0, "0" * 64)
            self._read()
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self.files.close()

    def _file(self, name: str) -> bytes:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.files.fd)
        try:
            self.files.private(fd)
            if os.fstat(fd).st_size > 16 * 1024**2:
                raise ValueError("Deletion journal unavailable")
            blocks = []
            while block := os.read(fd, 65536):
                blocks.append(block)
            return b"".join(blocks)
        finally:
            os.close(fd)

    def _head(self, count: int, digest: str) -> None:
        name = f".{uuid4()}.tmp"
        fd = os.open(
            name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=self.files.fd
        )
        try:
            body = json.dumps({"count": count, "digest": digest}, sort_keys=True).encode()
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(body)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        os.rename(name, "head.json", src_dir_fd=self.files.fd, dst_dir_fd=self.files.fd)
        os.fsync(self.files.fd)

    def _read(self) -> tuple[list[Tombstone], str]:
        try:
            head = strict_json(self._file("head.json").decode())
            if (
                not isinstance(head, dict)
                or set(head) != {"count", "digest"}
                or type(head["count"]) is not int
                or head["count"] < 0
            ):
                raise ValueError("Invalid deletion head")
            data = self._file("ledger.jsonl")
            if data and not data.endswith(b"\n"):
                raise ValueError("Partial deletion journal")
            records = []
            digests = ["0" * 64]
            seen = set()
            for line in data.splitlines():
                body = strict_json(line.decode())
                if not isinstance(body, dict) or set(body) != {"previous", "record", "digest"}:
                    raise ValueError("Invalid deletion entry")
                if body["previous"] != digests[-1] or body["digest"] != hashed(
                    {"previous": body["previous"], "record": body["record"]}
                ):
                    raise ValueError("Deletion chain mismatch")
                record = Tombstone.model_validate_json(json.dumps(body["record"]))
                if record.session_id in seen:
                    raise ValueError("Duplicate deletion marker")
                seen.add(record.session_id)
                records.append(record)
                digests.append(body["digest"])
            if head["count"] > len(records) or head["digest"] != digests[head["count"]]:
                raise ValueError("Deletion journal truncated")
            if head["count"] < len(records):
                self._head(len(records), digests[-1])
            return records, digests[-1]
        except Exception:
            raise ValueError("Deletion journal integrity failed") from None

    def entries(self) -> list[Tombstone]:
        with self.lock:
            return self._read()[0]

    def contains(self, session_id: UUID) -> bool:
        return any(record.session_id == session_id for record in self.entries())

    def record(
        self,
        session_id: UUID,
        reason: Literal["USER_REQUEST", "RETENTION_EXPIRED"],
        inventory_hash: str,
        deleted_ms: int,
    ) -> Tombstone:
        record = Tombstone(
            session_id=session_id,
            reason=reason,
            inventory_hash=inventory_hash,
            deleted_ms=deleted_ms,
        )
        with self.lock:
            records, previous = self._read()
            old = next((r for r in records if r.session_id == session_id), None)
            if old:
                if (old.reason, old.inventory_hash) != (record.reason, record.inventory_hash):
                    raise ContractError("IDEMPOTENCY_CONFLICT")
                return old
            body = {"previous": previous, "record": record.model_dump(mode="json")}
            digest = hashed(body)
            body["digest"] = digest
            encoded = (json.dumps(body, sort_keys=True) + "\n").encode()
            fd = os.open(
                "ledger.jsonl", os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=self.files.fd
            )
            try:
                self.files.private(fd)
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(fd)
            finally:
                os.close(fd)
            self._head(len(records) + 1, digest)
            return record
