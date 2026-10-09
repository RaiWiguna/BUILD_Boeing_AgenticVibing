"""Streaming multipart upload to private fd-backed staging; no framework temp spooling."""

import asyncio
import re
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from flowlens.auth.routes import cookie
from flowlens.clocks.normalization import ClockSpec
from flowlens.contracts.models import TimeRange
from flowlens.imports.commit import ImportCommit, ImportReceipt
from flowlens.imports.inspection import InvalidContent, strict_json
from flowlens.imports.metadata import ImportMetadata, MetadataRequest, PreparedImport
from flowlens.imports.staging import (
    FileSink,
    ImportFailure,
    ImportPreview,
    Imports,
    Issue,
    Role,
    UploadSession,
)
from flowlens.sources.metadata import (
    CoverageDeclaration,
    Declaration,
    FileDeclaration,
    HoldLine,
    IdentityDeclaration,
    Layout,
    Retention,
    RightsProfile,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect


def metadata_validation_error(error: ValidationError) -> ImportFailure:
    models = (
        MetadataRequest,
        Declaration,
        FileDeclaration,
        ClockSpec,
        RightsProfile,
        Retention,
        CoverageDeclaration,
        IdentityDeclaration,
        Layout,
        HoldLine,
        TimeRange,
    )
    names = {name for model in models for name in model.model_fields}
    failure = ImportFailure("INVALID_METADATA", "metadata")
    issues = []
    for item in error.errors(include_input=False, include_context=False)[:8]:
        location = item["loc"]
        safe = [
            str(part)
            for part in location
            if (isinstance(part, str) and part in names)
            or (type(part) is int and 0 <= part <= 1000)
        ]
        field = "metadata" + ("." + ".".join(safe) if safe else "")
        code = "INVALID_METADATA"
        if item["type"] == "literal_error" and location[-1:] == ("units",):
            code = "UNKNOWN_UNITS"
        elif location[-1:] == ("coordinate_system",):
            code = "UNSUPPORTED_COORDINATE_SYSTEM"
        elif location[-1:] == ("sha256",):
            code = "INVALID_HASH"
        elif "clock" in location:
            code = "INVALID_CLOCK"
        issues.append(
            Issue(
                code=code,
                field=field,
                remediation="Correct the indicated metadata field and submit a new revision.",
            )
        )
    failure.issues = issues
    return failure


class MultipartUpload:
    def __init__(self, session: UploadSession, boundary: bytes) -> None:
        self.session = session
        self.sink: FileSink | None = None
        self.headers: dict[bytes, bytes] = {}
        self.name, self.value = bytearray(), bytearray()
        self.ended = False
        self.parser = MultipartParser(
            boundary,
            {
                "on_part_begin": self.begin,
                "on_header_field": self.header_name,
                "on_header_value": self.header_value,
                "on_header_end": self.header_end,
                "on_headers_finished": self.headers_finished,
                "on_part_data": self.data,
                "on_part_end": self.part_end,
                "on_end": self.end,
            },
            max_header_count=8,
            max_header_size=2048,
        )

    def begin(self) -> None:
        self.headers.clear()
        self.name.clear()
        self.value.clear()
        self.sink = None

    def header_name(self, data: bytes, start: int, end: int) -> None:
        self.name.extend(data[start:end])

    def header_value(self, data: bytes, start: int, end: int) -> None:
        self.value.extend(data[start:end])

    def header_end(self) -> None:
        name = bytes(self.name).lower()
        if name in self.headers or len(self.name) + len(self.value) > 2048:
            raise ImportFailure("INVALID_MULTIPART_HEADERS")
        self.headers[name] = bytes(self.value)
        self.name.clear()
        self.value.clear()

    def headers_finished(self) -> None:
        raw_disposition = self.headers.get(b"content-disposition", b"")
        # Check before parsing: multipart's compatibility handling strips Windows paths.
        if b"\\" in raw_disposition or b"/" in raw_disposition:
            raise ImportFailure("INVALID_FILENAME")
        disposition, options = parse_options_header(raw_disposition)
        if disposition != b"form-data" or b"filename" not in options or b"name" not in options:
            raise ImportFailure("FILE_PART_REQUIRED")
        if self.headers.keys() - {b"content-disposition", b"content-type", b"x-content-sha256"}:
            raise ImportFailure("INVALID_MULTIPART_HEADERS")
        try:
            role = options[b"name"].decode("ascii")
            filename = options[b"filename"].decode("ascii")
            media_type = (
                self.headers.get(b"content-type", b"application/octet-stream")
                .decode("ascii")
                .split(";", 1)[0]
                .lower()
            )
            expected = self.headers.get(b"x-content-sha256")
            if role not in ("audio", "events", "tracks"):
                raise ImportFailure("UNKNOWN_FILE_ROLE")
            self.sink = self.session.add(
                cast(Role, role),
                filename,
                media_type,
                expected.decode("ascii") if expected else None,
            )
        except UnicodeError:
            raise ImportFailure("INVALID_MULTIPART_HEADERS") from None

    def data(self, data: bytes, start: int, end: int) -> None:
        if self.sink is None:
            raise ImportFailure("MALFORMED_MULTIPART")
        self.sink.write(data[start:end])

    def part_end(self) -> None:
        if self.sink is None:
            raise ImportFailure("MALFORMED_MULTIPART")
        self.sink.seal()

    def end(self) -> None:
        self.ended = True

    def feed(self, data: bytes) -> None:
        try:
            self.parser.write(data)
        except MultipartParseError:
            raise ImportFailure("MALFORMED_MULTIPART") from None

    def finish(self) -> ImportPreview:
        self.parser.finalize()
        if not self.ended:
            raise ImportFailure("INCOMPLETE_UPLOAD")
        return self.session.finish()


def service(request: Request) -> Imports:
    value: Imports | None = request.app.state.imports
    if value is None:
        raise HTTPException(503)
    return value


class CommitRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    expected_revision: int = Field(ge=1, le=64)


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/imports", tags=["Private import preview"])

    @router.post("", response_model=ImportPreview, status_code=201)
    async def upload(request: Request) -> ImportPreview:
        imports = service(request)
        kind, options = parse_options_header(request.headers.get("content-type", ""))
        boundary = options.get(b"boundary", b"")
        if kind != b"multipart/form-data" or not re.fullmatch(
            rb"[A-Za-z0-9'()+_,./:=?-]{1,70}", boundary
        ):
            raise ImportFailure("MULTIPART_REQUIRED")
        max_body = imports.limits.max_total_bytes + 1024**2
        declared = request.headers.get("content-length")
        if declared is not None and (
            not re.fullmatch(r"[0-9]{1,20}", declared) or int(declared) > max_body
        ):
            raise ImportFailure("TOTAL_SIZE_LIMIT")
        session = await run_in_threadpool(
            imports.start, cookie(request), request.headers.get("idempotency-key", "")
        )
        received = 0
        try:
            parser = MultipartUpload(session, boundary)
            try:
                async with asyncio.timeout(600):
                    async for block in request.stream():
                        received += len(block)
                        if received > max_body:
                            raise ImportFailure("TOTAL_SIZE_LIMIT")
                        await run_in_threadpool(parser.feed, block)
                    if declared is not None and int(declared) != received:
                        raise ImportFailure("INCOMPLETE_UPLOAD")
                    return await run_in_threadpool(parser.finish)
            except TimeoutError:
                raise ImportFailure("UPLOAD_TIMEOUT") from None
            except ClientDisconnect:
                raise ImportFailure("INCOMPLETE_UPLOAD") from None
        finally:
            await run_in_threadpool(session.abort)

    @router.get("/{import_id}", response_model=ImportPreview)
    def preview(request: Request, import_id: UUID) -> ImportPreview:
        return ImportMetadata(service(request)).current_preview(cookie(request), import_id)

    @router.post(
        "/{import_id}/metadata",
        response_model=PreparedImport,
        status_code=201,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["expected_revision", "declaration"],
                            "properties": {
                                "expected_revision": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 63,
                                },
                                "declaration": {"$ref": "#/components/schemas/Declaration"},
                            },
                        }
                    }
                },
            }
        },
    )
    async def metadata(request: Request, import_id: UUID) -> PreparedImport:
        imports = service(request)
        if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
            raise ImportFailure("JSON_REQUIRED", "metadata")
        body = bytearray()
        try:
            async with asyncio.timeout(60):
                async for block in request.stream():
                    if len(body) + len(block) > 1024**2:
                        raise ImportFailure("METADATA_SIZE_LIMIT", "metadata")
                    body.extend(block)
            strict_json(body.decode("utf-8"))
            payload = MetadataRequest.model_validate_json(body)
        except ValidationError as error:
            raise metadata_validation_error(error) from None
        except (InvalidContent, UnicodeError):
            raise ImportFailure("INVALID_METADATA", "metadata") from None
        except (TimeoutError, ClientDisconnect):
            raise ImportFailure("INCOMPLETE_UPLOAD", "metadata") from None
        return await run_in_threadpool(
            ImportMetadata(imports).prepare,
            cookie(request),
            import_id,
            request.headers.get("idempotency-key", ""),
            payload,
        )

    @router.get("/{import_id}/metadata", response_model=PreparedImport)
    def get_metadata(
        request: Request, import_id: UUID, revision: int | None = Query(default=None, ge=1, le=64)
    ) -> PreparedImport:
        return ImportMetadata(service(request)).get(cookie(request), import_id, revision=revision)

    @router.post(
        "/{import_id}/commit",
        response_model=ImportReceipt,
        status_code=201,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["expected_revision"],
                            "properties": {
                                "expected_revision": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 64,
                                }
                            },
                        }
                    }
                },
            }
        },
    )
    async def commit_import(request: Request, import_id: UUID) -> ImportReceipt:
        commits: ImportCommit | None = request.app.state.import_commits
        if commits is None:
            raise HTTPException(503)
        body = bytearray()
        try:
            async with asyncio.timeout(60):
                async for block in request.stream():
                    if len(body) + len(block) > 4096:
                        raise ImportFailure("COMMIT_SIZE_LIMIT", "commit")
                    body.extend(block)
            if (
                request.headers.get("content-type", "").split(";", 1)[0].lower()
                != "application/json"
            ):
                raise ImportFailure("JSON_REQUIRED", "commit")
            strict_json(body.decode("utf-8"))
            payload = CommitRequest.model_validate_json(body)
        except (InvalidContent, UnicodeError, ValidationError):
            raise ImportFailure("INVALID_COMMIT", "commit") from None
        except (TimeoutError, ClientDisconnect):
            raise ImportFailure("INCOMPLETE_UPLOAD", "commit") from None
        return await run_in_threadpool(
            commits.commit,
            cookie(request),
            import_id,
            payload.expected_revision,
            request.headers.get("idempotency-key", ""),
        )

    return router
