"""Local Paket A host settings; production composition is not available yet."""

from collections.abc import Mapping
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from flowlens.core.config import Profile
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HostSettings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    profile: Profile = "development"
    api_workers: Literal[1] = 1
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    contract_version: Literal["1.0.0"] = "1.0.0"
    database_path: Path | None = None
    public_origin: str | None = None
    import_staging_path: Path | None = None
    raw_assets_path: Path | None = None
    artifact_staging_path: Path | None = None

    @field_validator("public_origin")
    @classmethod
    def valid_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("A single HTTP(S) origin is required.")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("Invalid origin port.")
        if parsed.scheme == "http" and parsed.hostname != "localhost":
            if not ip_address(parsed.hostname).is_loopback:
                raise ValueError("HTTP auth is restricted to loopback origins.")
        return value.rstrip("/")

    @model_validator(mode="after")
    def staging_requires_database(self) -> Self:
        if self.import_staging_path is not None:
            if self.database_path is None:
                raise ValueError("Import staging requires a configured database.")
            if self.import_staging_path.absolute() == self.database_path.absolute().parent:
                raise ValueError("Staging requires a separate directory.")
        if self.raw_assets_path is not None:
            if self.database_path is None or self.import_staging_path is None:
                raise ValueError("Raw storage requires database and import staging")
            roots = (
                self.raw_assets_path.absolute(),
                self.import_staging_path.absolute(),
                self.database_path.absolute().parent,
            )
            if any(
                a == b or a in b.parents or b in a.parents
                for index, a in enumerate(roots)
                for b in roots[index + 1 :]
            ):
                raise ValueError("Private storage directories must be separate")
        if self.artifact_staging_path is not None:
            if (
                self.raw_assets_path is None
                or self.import_staging_path is None
                or self.database_path is None
            ):
                raise ValueError("Artifacts require configured source storage")
            path = self.artifact_staging_path.absolute()
            roots = (
                self.raw_assets_path.absolute(),
                self.import_staging_path.absolute(),
                self.database_path.absolute().parent,
            )
            if any(path == root or path in root.parents or root in path.parents for root in roots):
                raise ValueError("Artifact storage requires a separate root")
        return self

    @property
    def origin(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return self.public_origin or f"http://{host}:{self.port}"

    @field_validator("api_workers", "port", mode="before")
    @classmethod
    def integer_only(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("An integer is required.")
        return value

    @field_validator("host")
    @classmethod
    def local_bind(cls, value: str) -> str:
        if not ip_address(value).is_loopback:
            raise ValueError("The incomplete host must bind to loopback.")
        return value

    @field_validator("profile")
    @classmethod
    def incomplete_host(cls, value: Profile) -> Profile:
        if value == "production":
            raise ValueError("Production requires completed A/B composition and G-BE.")
        return value

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> Self:
        fields = {
            "FLOWLENS_PROFILE": "profile",
            "FLOWLENS_API_WORKERS": "api_workers",
            "FLOWLENS_HOST": "host",
            "FLOWLENS_PORT": "port",
            "FLOWLENS_DB_PATH": "database_path",
            "FLOWLENS_ORIGIN": "public_origin",
            "FLOWLENS_IMPORT_STAGING_PATH": "import_staging_path",
            "FLOWLENS_RAW_ASSETS_PATH": "raw_assets_path",
            "FLOWLENS_ARTIFACT_STAGING_PATH": "artifact_staging_path",
        }
        if any(key.startswith("FLOWLENS_") and key not in fields for key in environment):
            raise ValueError("Unsupported host configuration key.")
        for key in ("WEB_CONCURRENCY", "UVICORN_WORKERS"):
            if key in environment and environment[key] != "1":
                raise ValueError("Only one API process is supported.")
        values: dict[str, object] = {}
        for key, field in fields.items():
            if key in environment:
                raw = environment[key]
                if field in (
                    "database_path",
                    "import_staging_path",
                    "raw_assets_path",
                    "artifact_staging_path",
                ):
                    if not raw.strip() or "://" in raw:
                        raise ValueError("A local database file path is required.")
                    values[field] = Path(raw)
                elif field in ("api_workers", "port"):
                    if not raw.isascii() or not raw.isdecimal():
                        raise ValueError("Invalid integer host setting.")
                    values[field] = int(raw)
                else:
                    values[field] = raw
        return cls.model_validate(values)
