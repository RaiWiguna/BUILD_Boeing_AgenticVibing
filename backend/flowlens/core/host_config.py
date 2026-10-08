"""Local Paket A host settings; production composition is not available yet."""

from collections.abc import Mapping
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Self

from flowlens.core.config import Profile
from pydantic import BaseModel, ConfigDict, Field, field_validator


class HostSettings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    profile: Profile = "development"
    api_workers: Literal[1] = 1
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    contract_version: Literal["1.0.0"] = "1.0.0"
    database_path: Path | None = None

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
                if field == "database_path":
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
