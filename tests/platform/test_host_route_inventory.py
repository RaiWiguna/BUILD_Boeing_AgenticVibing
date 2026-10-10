"""Composition inventory must include lazily included HTTP and WS platform routes."""

import pytest
from fastapi import APIRouter
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings
from flowlens.core.modules import ModuleRegistration


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("transport", ["HTTP", "WEBSOCKET"])
def test_registered_module_cannot_shadow_included_platform_routes(nested, transport):
    child = APIRouter()
    path = "/sessions" if nested else "/api/v1/sessions"
    if transport == "HTTP":
        child.get(path)(lambda: {})
    else:
        child.websocket(path + "/{session_id}/stream")(lambda: None)
    router = APIRouter()
    if nested:
        router.include_router(child, prefix="/api/v1")
    else:
        router = child
    with pytest.raises(ValueError, match="route"):
        create_host(
            HostSettings(profile="test"),
            modules=[ModuleRegistration(name="collision", routes=(router,))],
        )


def test_nested_prefixes_with_distinct_routes_remain_allowed():
    child, parent = APIRouter(), APIRouter()
    child.get("/status")(lambda: {"status": "ready"})
    parent.include_router(child, prefix="/api/v1/analysis")
    app = create_host(
        HostSettings(profile="test"),
        modules=[ModuleRegistration(name="analysis", routes=(parent,))],
    )
    assert "/api/v1/analysis/status" in app.openapi()["paths"]
