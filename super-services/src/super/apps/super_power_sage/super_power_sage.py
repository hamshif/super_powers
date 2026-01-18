"""FastAPI app for Super Power Sage."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from super.apps.super_power_sage.agent import SageGraphFactory
from super.config import get_app_conf

# Configure a logger for this module
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str


class ChatRequest(BaseModel):
    prompt: str


# Global reference to the compiled graph
_graph = None


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
    global _graph
    
    conf = get_app_conf(app="super_power_sage")
    level = conf.get_string("super_power_sage.logging.level", "INFO")
    _apply_log_level(level)
    logger.info("Super Power Sage starting up...")

    # Initialize Agent
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        logger.warning("OMGENE_OPEN_AI_API_KEY not found! Agent will fail if called.")
    
    # Dependency Injection: Inject OpenAI model
    model = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    _graph = SageGraphFactory.create_graph(model)
    logger.info("Agent graph initialized.")
    
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


async def _chat_stream(prompt: str) -> AsyncGenerator[str, None]:
    """Streams responses from the LangGraph agent."""
    if not _graph:
         yield _format_sse("Error: Agent graph not initialized.", event="message")
         return

    try:
        inputs = {"messages": [HumanMessage(content=prompt)]}
        async for event in _graph.astream(inputs, stream_mode="updates"):
            # LangGraph 'updates' mode yields dicts of node updates.
            # We look for the 'model' node output.
            for node_name, node_output in event.items():
                if "messages" in node_output:
                    # Get the last message content
                    last_message = node_output["messages"][-1]
                    content = last_message.content
                    if content:
                         yield _format_sse(content, event="message")

    except Exception as e:
        logger.error(f"Error calling agent: {e}", exc_info=True)
        yield _format_sse(f"Error processing request: {str(e)}", event="message")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/super_powers_sage")
async def super_powers_sage(request: ChatRequest) -> StreamingResponse:
    logger.debug("Received request: prompt=%s", request.prompt)

    async def event_generator():
        # Yield an initial ping/comment to force headers to be sent immediately
        yield ": ping\n\n"
        
        # Then yield the actual response stream
        async for chunk in _chat_stream(request.prompt):
             yield chunk

    headers = {
        "Cache-Control": "no-cache", 
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
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
