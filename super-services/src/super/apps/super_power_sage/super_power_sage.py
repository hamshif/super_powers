"""FastAPI app for Super Power Sage."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from super.config import get_app_conf

# Configure a logger for this module
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str


class ChatRequest(BaseModel):
    prompt: str


class SuperPowerSageAgent:
    def respond(self, prompt: str) -> str:
        return f"Sage says: {prompt}"


_agent = SuperPowerSageAgent()


def _apply_log_level(level: str) -> None:
    """Apply log level to the root logger and all handlers."""
    resolved = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(resolved)
    
    # Ensure standard output handler exists if none presence
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(resolved)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    
    for handler in root.handlers:
        handler.setLevel(resolved)
    
    logger.info(f"Log level set to {level} (resolved: {resolved})")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup logic
    conf = get_app_conf(app="super_power_sage")
    level = conf.get_string("super_power_sage.logging.level", "INFO")
    _apply_log_level(level)
    logger.info("Super Power Sage starting up...")
    
    yield
    
    # Shutdown logic
    logger.info("Super Power Sage shutting down...")


app = FastAPI(title="Super Power Sage", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _format_sse(data: str, event: str | None = None) -> str:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


async def _chat_stream(prompt: str) -> str:
    response = _agent.respond(prompt)
    if not response:
        logger.warning(f"Agent returned empty response for prompt: {prompt}")
        return _format_sse("Thinking...", event="message")
    return _format_sse(response, event="message")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/super_powers_sage")
async def super_powers_sage(request: ChatRequest) -> StreamingResponse:
    logger.debug("Received request: prompt=%s", request.prompt)

    async def event_generator():
        # Yield an initial ping/comment to force headers to be sent immediately
        yield ": ping\n\n"
        
        # Then yield the actual response
        result = await _chat_stream(request.prompt)
        logger.debug("Yielding result: %s", result)
        yield result

    headers = {
        "Cache-Control": "no-cache", 
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Disable proxy buffering if any
    }
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


def main() -> None:
    conf = get_app_conf(app="super_power_sage")
    host = conf.get_string("super_power_sage.server.host")
    port = conf.get_int("super_power_sage.server.port")
    reload = conf.get_bool("super_power_sage.server.reload")
    log_level = conf.get_string("super_power_sage.logging.level", "INFO").lower()

    # Basic config for initial startup before lifespan kicks in
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

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
            log_level=log_level,
        )
    else:
        uvicorn.run(app, host=host, port=port, reload=False, log_level=log_level)


if __name__ == "__main__":
    main()
