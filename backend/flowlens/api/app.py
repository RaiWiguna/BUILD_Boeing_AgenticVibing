"""Contract-only app factory. No business API is advertised as implemented."""

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from flowlens import CONTRACT_VERSION
from flowlens.contracts.models import INTERNAL_MODELS, PUBLIC_MODELS, Contract
from flowlens.core.config import Profile, Settings
from flowlens.core.errors import HTTP_STATUS, ContractError, ErrorResponse
from flowlens.testing.harness import build_harness


def create_app(profile: Profile = "development", track: Literal["A", "B"] = "A") -> FastAPI:
    settings = Settings(profile=profile)
    bundle = build_harness(track)
    app = FastAPI(
        title="FlowLens baseline contract harness (MOCK)",
        version=CONTRACT_VERSION,
        description="Phase 1 contract validation only; no production business routes.",
    )
    app.state.settings = settings
    app.state.bundle = bundle

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Locations only; error input/context can contain transcript, credentials or paths.
        error = ErrorResponse(
            code="INVALID_INPUT",
            message="Request does not match the contract.",
            request_id=str(uuid4()),
            field_issues=[".".join(map(str, row["loc"])) for row in exc.errors()],
        )
        return JSONResponse(status_code=422, content=error.model_dump())

    @app.exception_handler(ContractError)
    async def contract_error(request: Request, exc: ContractError) -> JSONResponse:
        error = ErrorResponse(
            code=exc.code, message="Request cannot be accepted.", request_id=str(uuid4())
        )
        return JSONResponse(status_code=HTTP_STATUS[exc.code], content=error.model_dump())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "alive", "profile": "MOCK"}

    @app.get("/ready")
    def ready() -> dict[str, str | bool]:
        return {"ready": False, "implementation": "BASELINE_ONLY", "profile": "MOCK"}

    @app.get("/release.json")
    def release() -> dict[str, str]:
        return {"contract_version": CONTRACT_VERSION, "implementation": "BASELINE_ONLY"}

    for module in bundle.registry.modules:
        for router in module.routes:
            app.include_router(router)
    for model in (*PUBLIC_MODELS, *INTERNAL_MODELS):
        add_validator(app, model)
    return app


def add_validator(app: FastAPI, model: type[Contract]) -> None:
    def validate(payload: Contract) -> Contract:
        return payload

    validate.__annotations__ = {"payload": model, "return": model}
    aliases = {
        "TranscriptSegment": "transcript",
        "SourceManifest": "manifest",
        "JobResult": "job_result",
        "RequestContext": "context",
    }
    name = aliases.get(model.__name__, model.__name__.lower())
    app.post(
        f"/_harness/validate/{name}",
        response_model=model,
        operation_id=f"validate{model.__name__}",
        tags=["MOCK contract validation"],
    )(validate)
