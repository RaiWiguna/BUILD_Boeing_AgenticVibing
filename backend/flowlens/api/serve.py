"""Supported local launcher: one API process, no reload, no access payload logs."""

from os import environ

import uvicorn
from flowlens.api.host import create_host
from flowlens.core.host_config import HostSettings


def main() -> None:
    try:
        settings = HostSettings.from_environment(environ)
        app = create_host(settings)
    except ValueError:
        raise SystemExit("Invalid host configuration; check the documented settings.") from None
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        workers=1,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
