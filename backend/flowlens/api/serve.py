"""Supported local launcher: one API process, no reload, no access payload logs."""

from os import environ

import uvicorn
from flowlens.core.host_config import HostSettings
from flowlens.integration import create_integrated_host
from flowlens.ops.logs import configure


def main() -> None:
    try:
        settings = HostSettings.from_environment(environ)
        app = create_integrated_host(settings)
    except ValueError:
        raise SystemExit("Invalid host configuration; check the documented settings.") from None
    configure()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        workers=1,
        reload=False,
        access_log=False,
        proxy_headers=False,
        ws="wsproto",
        ws_max_size=1024,
    )


if __name__ == "__main__":
    main()
