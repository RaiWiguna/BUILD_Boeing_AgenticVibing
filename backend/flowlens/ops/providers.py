"""Immutable admin profile versions and sanitized frozen ProviderAdapter checks."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, ValidationError

from flowlens.auth.accounts import Account
from flowlens.auth.sessions import Sessions, token_hash
from flowlens.clocks.normalization import MetadataModel
from flowlens.contracts.models import ProviderProfile
from flowlens.contracts.ports import ProviderAdapter
from flowlens.core.errors import ContractError
from flowlens.imports.metadata import hashed
from flowlens.storage.sqlite.database import Database, UnitOfWork


class ProviderOptions(MetadataModel):
    project_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{4,62}$")] | None = None
    recognizer_id: Annotated[str, Field(pattern=r"^[a-z0-9_-]{1,64}$")] | None = None
    word_timestamps: bool | None = None
    adaptation_version: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")] | None = None
    terms_profile: Literal["PAID", "UNPAID", "UNVERIFIED"] = "UNVERIFIED"
    credential_ref: Literal["GOOGLE_ADC", "GEMINI_KEY_FILE", "UNCONFIGURED"] = "UNCONFIGURED"


@dataclass(frozen=True)
class AdapterBinding:
    adapter: ProviderAdapter
    mock: bool
    options: ProviderOptions = field(default_factory=ProviderOptions)


Failure = Literal[
    "ADAPTER_NOT_CONFIGURED", "ADAPTER_UNAVAILABLE", "INVALID_DIAGNOSTIC", "CONFIG_NOT_BOUND"
]


class ProfileView(MetadataModel):
    profile: ProviderProfile
    options: ProviderOptions = ProviderOptions()
    revision: int
    config_hash: str
    verification: Literal["UNVERIFIED", "MOCK", "ADAPTER_REPORTED", "UNAVAILABLE"]
    provider_verified: Literal[False] = False
    failure_code: (
        Literal[
            "ADAPTER_NOT_CONFIGURED",
            "ADAPTER_UNAVAILABLE",
            "INVALID_DIAGNOSTIC",
            "CONFIG_NOT_BOUND",
        ]
        | None
    ) = None
    checked_ms: int | None = None


def validate_profile(value: ProviderProfile) -> ProviderProfile:
    try:
        value = ProviderProfile.model_validate_json(value.model_dump_json())
    except (ValidationError, ValueError):
        raise ContractError("INVALID_INPUT") from None
    expected = (
        "STT_V2_INLINE" if value.provider == "GOOGLE_STT" else "GEMINI_DEVELOPER_INTERACTIONS"
    )
    if (
        value.transport != expected
        or value.readiness != "UNVERIFIED"
        or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,127}", value.model)
        or (value.provider == "GEMINI" and not value.model.startswith("gemini-"))
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value.version)
        or any(
            v is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", v)
            for v in (value.region, value.locale)
        )
        or (value.provider == "GOOGLE_STT" and (value.region is None or value.locale is None))
    ):
        raise ContractError("INVALID_INPUT")
    return value


class Providers:
    def __init__(
        self,
        database: Database,
        sessions: Sessions,
        *,
        adapters: Mapping[str, AdapterBinding] | None = None,
        allow_mock: bool = False,
    ) -> None:
        self.database, self.sessions = database, sessions
        self.adapters = dict(adapters or {})
        if any(
            k not in ("GOOGLE_STT", "GEMINI") or (v.mock and not allow_mock)
            for k, v in self.adapters.items()
        ):
            raise ValueError("Explicit provider registration/profile required")

    def admin(self, uow: UnitOfWork, token: str) -> Account:
        actor = self.sessions.authenticate(uow, token_hash(token))
        if not actor.is_admin:
            raise ContractError("ACCESS_DENIED")
        return actor

    def _latest(self, uow: UnitOfWork, pid: UUID) -> ProfileView:
        row = uow.connection.execute(
            "SELECT payload FROM platform_provider_profiles WHERE id=? ORDER BY "
            "revision DESC LIMIT 1",
            (str(pid),),
        ).fetchone()
        if row is None:
            raise ContractError("EVIDENCE_UNAVAILABLE")
        view = ProfileView.model_validate_json(row[0])
        check = uow.connection.execute(
            "SELECT payload FROM platform_provider_checks WHERE profile_id=? AND "
            "revision=? ORDER BY rowid DESC LIMIT 1",
            (str(pid), view.revision),
        ).fetchone()
        return ProfileView.model_validate_json(check[0]) if check else view

    def _receipt(
        self, uow: UnitOfWork, actor: UUID, operation: str, key: str, request_hash: str
    ) -> ProfileView | None:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", key):
            raise ContractError("INVALID_INPUT")
        row = uow.connection.execute(
            "SELECT request_hash,result FROM platform_ops_requests WHERE "
            "actor_id=? AND operation=? AND key_hash=?",
            (str(actor), operation, hashed(key)),
        ).fetchone()
        if row and row[0] != request_hash:
            raise ContractError("IDEMPOTENCY_CONFLICT")
        return ProfileView.model_validate_json(row[1]) if row else None

    def _record(
        self,
        uow: UnitOfWork,
        actor: UUID,
        operation: str,
        key: str,
        request_hash: str,
        result: ProfileView,
    ) -> None:
        uow.connection.execute(
            "INSERT INTO platform_ops_requests VALUES (?,?,?,?,?)",
            (str(actor), operation, hashed(key), request_hash, result.model_dump_json()),
        )
        uow.connection.execute(
            "INSERT INTO "
            "platform_ops_audit(actor_id,action,object_id,version,created_ms) VALUES (?,?,?,?,?)",
            (str(actor), operation, str(result.profile.id), result.revision, self.sessions.clock()),
        )

    def save(
        self,
        token: str,
        profile: ProviderProfile,
        *,
        expected_version: int,
        key: str,
        options: ProviderOptions | None = None,
    ) -> ProfileView:
        profile = validate_profile(profile)
        options = options if options is not None else ProviderOptions()
        try:
            options = ProviderOptions.model_validate_json(options.model_dump_json())
        except (ValidationError, ValueError):
            raise ContractError("INVALID_INPUT") from None
        metadata = profile.model_dump_json() + options.model_dump_json()
        if re.search(
            r"AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|gh[pousr]_[0-9A-Za-z]{36}"
            r"|github_pat_[0-9A-Za-z_]{40,}|xox[baprs]-[0-9A-Za-z-]{20,}",
            metadata,
        ):
            raise ContractError("INVALID_INPUT")
        if type(expected_version) is not int or not 0 <= expected_version < 32:
            raise ContractError("INVALID_INPUT")
        digest = hashed(
            [profile.model_dump(mode="json"), options.model_dump(mode="json"), expected_version]
        )
        with self.database.begin() as uow:
            actor = self.admin(uow, token)
            old = self._receipt(uow, actor.id, "PROVIDER_CONFIGURED", key, digest)
            if old:
                return old
            revision = uow.connection.execute(
                "SELECT COALESCE(MAX(revision),0) FROM platform_provider_profiles WHERE id=?",
                (str(profile.id),),
            ).fetchone()[0]
            if revision != expected_version:
                raise ContractError("VERSION_CONFLICT")
            if (
                revision == 0
                and uow.connection.execute(
                    "SELECT COUNT(DISTINCT id) FROM platform_provider_profiles"
                ).fetchone()[0]
                >= 100
            ):
                raise ContractError("NOT_EVALUABLE")
            result = ProfileView(
                profile=profile,
                revision=revision + 1,
                config_hash=hashed(
                    [profile.model_dump(mode="json"), options.model_dump(mode="json")]
                ),
                options=options,
                verification="UNVERIFIED",
            )
            uow.connection.execute(
                "INSERT INTO platform_provider_profiles VALUES (?,?,?,?,?,?)",
                (
                    str(profile.id),
                    result.revision,
                    result.config_hash,
                    result.model_dump_json(),
                    str(actor.id),
                    self.sessions.clock(),
                ),
            )
            self._record(uow, actor.id, "PROVIDER_CONFIGURED", key, digest, result)
            uow.commit()
            return result

    def check(
        self, token: str, identifier: UUID, *, expected_version: int, key: str
    ) -> ProfileView:
        digest = hashed([str(identifier), expected_version])
        with self.database.begin() as uow:
            actor = self.admin(uow, token)
            old = self._receipt(uow, actor.id, "PROVIDER_CHECKED", key, digest)
            if old:
                return old
            view = self._latest(uow, identifier)
            if type(expected_version) is not int or view.revision != expected_version:
                raise ContractError("VERSION_CONFLICT")
            if (
                uow.connection.execute(
                    "SELECT COUNT(*) FROM platform_provider_checks "
                    "WHERE profile_id=? AND revision=?",
                    (str(identifier), view.revision),
                ).fetchone()[0]
                >= 100
            ):
                raise ContractError("NOT_EVALUABLE")
        # No provider work while holding the SQLite lock; callback gets metadata only.
        base = view.profile.model_copy(update={"readiness": "UNVERIFIED"})
        binding = self.adapters.get(base.provider)
        status = "UNAVAILABLE"
        failure: Failure | None = "ADAPTER_NOT_CONFIGURED"
        verification: Literal["UNVERIFIED", "MOCK", "ADAPTER_REPORTED", "UNAVAILABLE"] = (
            "UNAVAILABLE"
        )
        if binding and binding.options != view.options:
            failure = "CONFIG_NOT_BOUND"
        elif binding:
            try:
                returned = ProviderProfile.model_validate_json(
                    binding.adapter.check(base).model_dump_json()
                )
                if returned.model_copy(update={"readiness": "UNVERIFIED"}) != base:
                    failure = "INVALID_DIAGNOSTIC"
                else:
                    status, failure = returned.readiness, None
                    verification = "MOCK" if binding.mock else "ADAPTER_REPORTED"
            except Exception:
                failure = "ADAPTER_UNAVAILABLE"
        result = ProfileView(
            profile=base.model_copy(update={"readiness": status}),
            options=view.options,
            revision=view.revision,
            config_hash=view.config_hash,
            verification=verification,
            failure_code=failure,
            checked_ms=self.sessions.clock(),
        )
        with self.database.begin() as uow:
            current = self.admin(uow, token)
            old = self._receipt(uow, current.id, "PROVIDER_CHECKED", key, digest)
            if old:
                return old
            if current.id != actor.id or self._latest(uow, identifier).revision != view.revision:
                raise ContractError("VERSION_CONFLICT")
            uow.connection.execute(
                "INSERT INTO platform_provider_checks VALUES (?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    str(identifier),
                    view.revision,
                    result.model_dump_json(),
                    str(actor.id),
                    self.sessions.clock(),
                ),
            )
            self._record(uow, actor.id, "PROVIDER_CHECKED", key, digest, result)
            uow.commit()
        return result

    def inventory(self, token: str) -> list[ProfileView]:
        with self.database.begin() as uow:
            self.admin(uow, token)
            return [
                self._latest(uow, UUID(r[0]))
                for r in uow.connection.execute(
                    "SELECT DISTINCT id FROM platform_provider_profiles ORDER BY id"
                )
            ]

    def history(self, token: str, identifier: UUID) -> list[ProfileView]:
        with self.database.begin() as uow:
            self.admin(uow, token)
            return [
                ProfileView.model_validate_json(r[0])
                for r in uow.connection.execute(
                    "SELECT payload FROM platform_provider_profiles WHERE id=? ORDER BY revision",
                    (str(identifier),),
                )
            ]
