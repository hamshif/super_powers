"""FastAPI app for Super Power Sage."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from super.config import get_app_conf


class HealthResponse(BaseModel):
    status: str


app = FastAPI(title="Super Power Sage")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def main() -> None:
    conf = get_app_conf(app="super_power_sage")
    host = conf.get_string("super_power_sage.server.host")
    port = conf.get_int("super_power_sage.server.port")
    reload = conf.get_bool("super_power_sage.server.reload")

    if reload:
        # Uvicorn reload requires an import string; ensure package root is on sys.path.
        import sys
        from pathlib import Path

        package_root = Path(__file__).resolve().parents[3]
        if package_root.as_posix() not in sys.path:
            sys.path.insert(0, package_root.as_posix())

        uvicorn.run(
            "super.apps.super_power_sage.super_power_sage:app",
            host=host,
            port=port,
            reload=True,
        )
    else:
        uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
