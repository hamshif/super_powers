"""FastAPI app for Super Power Sage."""

from __future__ import annotations

import logging
import os
import sys
import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver 
from pydantic import BaseModel

from super.apps.super_power_sage.agent import SageGraphFactory
from super.config import get_app_conf
from super.core import utils
from super.apps.super_power_sage import state

# Configure a logger for this module
logger = logging.getLogger(__name__)

from pathlib import Path
# Define project root early for use in endpoints
# file is in .../src/super/apps/super_power_sage/super_power_sage.py
# parents: [0]super_power_sage [1]apps [2]super [3]src [4]super-services [5]project_repo_root
project_root = Path(__file__).parents[5]



class HealthResponse(BaseModel):
    status: str


class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"




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
    global _graph, _gm_instance
    conf = get_app_conf(app="super_power_sage")
    
    _apply_log_level(conf.get_string("super_power_sage.logging.level", "INFO"))
    logger.info("Super Power Sage starting up...")
    
    # 1. Initialize LangGraph Agent
    logger.info("Initializing Super Power Sage Agent...")
    
    # Initialize Checkpointer
    checkpointer = MemorySaver()
    
    # Uses robust initialization with active rate-limit check and fallback
    try:
        model = utils.get_valid_llm(model_name="gpt-3.5-turbo")
    except (RuntimeError, ValueError) as e:
        logger.error(f"Failed to initialize Agent Model (Quota/Key issue): {e}")
        logger.warning("STARTING IN MOCK/OFFLINE MODE. Chat will fail until valid keys are provided.")
        # Fallback to a dummy model so the server starts. 
        # Runtime calls will fail gracefully in the chat stream.
        model = ChatOpenAI(api_key="sk-mock-key-to-allow-startup", model="gpt-3.5-turbo")

    _graph = SageGraphFactory.create_graph(model, checkpointer=checkpointer)
    logger.info("Agent Graph initialized.")
    
    # 2. Initialize Ray and Actors (CRITICAL DEPENDENCY)
    try:
        import ray
        from super.apps.generate_powers.worker import HeroGenerator
        from super.apps.super_power_sage.services.graph_service import GraphService
        from super.apps.super_power_sage import state

        if not ray.is_initialized():
             ray.init(ignore_reinit_error=True)
             logger.info("Ray Initialized.")
        
        # HeroGenerator
        state.hero_generator = HeroGenerator.remote()
        logger.info("HeroGenerator Actor started.")

        # GraphService (Async Graph Gen)
        warehouse_path = str(project_root / "data/warehouse")
        conf = get_app_conf(app="super_power_sage")
        def_hero = conf.get_string("super_power_sage.graph.default_hero", "Bugs Bunny")
        def_k = conf.get_int("super_power_sage.graph.default_neighbors", 5)
        
        state.graph_service = GraphService.remote(warehouse_path, def_hero, def_k)
        logger.info("GraphService Actor started.")
        
    except ImportError as e:
        logger.critical(f"MISSING DEPENDENCY: Ray is required. Please install: pip install 'ray[default]'. Error: {e}")
        raise e # Stop startup
    except Exception as e:
        logger.error(f"Failed to initialize Ray Actors: {e}", exc_info=True)
        raise e # Stop startup

    yield
    
    # Shutdown logic
    logger.info("Shutting down Super Power Sage...")
    _graph = None
    if ray.is_initialized():
        ray.shutdown()
        logger.info("Ray shutdown.")



app = FastAPI(title="Super Power Sage", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)





from super.apps.super_power_sage.models import SseEventType

def _format_sse(data: str, event: SseEventType | None = None) -> str:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event.value}")
    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


async def _chat_stream(prompt: str, session_id: str) -> AsyncGenerator[str, None]:
    """Streams responses from the LangGraph agent."""
    if not _graph:
         yield _format_sse("Error: Agent graph not initialized.", event=SseEventType.ANSWER)
         return

    try:
        inputs = {"messages": [HumanMessage(content=prompt)]}
        config = {"configurable": {"thread_id": session_id}}

        # Manual iteration to support heartbeat
        iterator = _graph.astream(inputs, config=config, stream_mode="updates")
        
        # Helper to get next chunk
        async def get_next_chunk():
             try:
                 return await iterator.__anext__()
             except StopAsyncIteration:
                 return None

        import random
        thinking_messages = [
            "Consulting the archives...",
            "Synthesizing genetic data...",
            "Checking the multiverse...",
            "Running quantum simulations...",
            "Asking the Oracle...",
            "Formatting response..."
        ]

        next_task = asyncio.create_task(get_next_chunk())
        
        # Track graph updates to prevent spamming the UI
        graph_update_sent = False

        while True:
            # Drain the queue for HERO_DATA events
            while state.data_queue:
                data_item = state.data_queue.pop(0)
                
                # LIMIT LOGIC: Only send 'hero'/'center' trigger ONCE per session/stream
                if 'hero' in data_item or 'center' in data_item:
                    if graph_update_sent:
                        # Strip trigger fields preventing frontend refresh
                        data_item.pop('hero', None)
                        data_item.pop('center', None)
                        logger.debug("Stripped graph trigger from subsequent data item")
                    else:
                        graph_update_sent = True
                        logger.debug("Emitting primary graph trigger")

                yield _format_sse(
                    json.dumps(data_item),
                    event=SseEventType.HERO_DATA
                )

            done, pending = await asyncio.wait([next_task], timeout=3.0)

            if next_task in done:
                # Graph task completed, get the next chunk
                try:
                    chunk = next_task.result()
                except StopAsyncIteration:
                    # Stream has ended
                    break
                except Exception as e:
                    logger.error(f"Error during graph stream: {e}", exc_info=True)
                    yield _format_sse(f"Error processing request: {str(e)}", event=SseEventType.ANSWER)
                    break
                
                if chunk is None:
                    break

                # Process the chunk (which is a dictionary of node updates)
                for node_name, node_update in chunk.items():
                    if "messages" in node_update:
                        last_message = node_update["messages"][-1]
                        
                        # Check for tool_calls (AIMessage)
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                                for tool_call in last_message.tool_calls:
                                    tool_name = tool_call.get("name", "unknown")
                                    logger.debug(f"Agent calling tool: {tool_name}")
                                    yield _format_sse(f"Using tool {tool_name}...", event=SseEventType.STREAM_OF_THOUGHT)

                        content = last_message.content
                        if content:
                                # Standard content is the Answer
                                yield _format_sse(content, event=SseEventType.ANSWER)
                    
                    # Also catching 'manage_context' updates or other node outputs if we want to show them as thought
                    if node_name == "manage_context":
                         # We could show intent updates here if desired
                         yield _format_sse("Updating context & intents...", event=SseEventType.STREAM_OF_THOUGHT)

                
                # Start waiting for next chunk
                next_task = asyncio.create_task(get_next_chunk())
            
            else:
                # Timeout / Still Pending -> Heartbeat
                msg = random.choice(thinking_messages)
                yield _format_sse(msg, event=SseEventType.HEARTBEAT)
                # Loop back to wait for the SAME next_task

    except Exception as e:
        logger.error(f"Error calling agent: {e}", exc_info=True)
        yield _format_sse(f"Error processing request: {str(e)}", event=SseEventType.ANSWER)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/super_powers_sage/visualize_graph", response_class=HTMLResponse)
async def visualize_graph(center: str = Query(None)):
    """
    Returns the generated HTML for the graph visualization.
    Fetches the graph asynchronously from the GraphService Ray Actor.
    """
    try:
        if state.graph_service is None:
             return HTMLResponse("<h1>Graph Service Unavailable (Ray not connected)</h1>", status_code=503)

        # Non-blocking remote call
        html_content = await state.graph_service.get_html.remote(center)
        return HTMLResponse(content=html_content, status_code=200)

    except Exception as e:
        logger.error(f"Graph viz failed: {e}", exc_info=True)
        return HTMLResponse(f"<h3>Error generating graph: {e}</h3>", status_code=500)


@app.get("/super_powers_sage/graph_data")
async def graph_data(center: str = Query(None)):
    """
    Returns JSON graph data for client-side rendering.
    Fetches asynchronously from the GraphService Ray Actor.
    """
    try:
        if state.graph_service is None:
             return JSONResponse({"error": "Graph Service Unavailable"}, status_code=503)

        # Non-blocking remote call
        data = await state.graph_service.get_graph_data.remote(center)
        return JSONResponse(content=data, status_code=200)

    except Exception as e:
        logger.error(f"Graph data fetch failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/super_powers_sage")
async def super_powers_sage(request: ChatRequest) -> StreamingResponse:
    logger.debug("Received request: prompt=%s session=%s", request.prompt, request.session_id)

    async def event_generator():
        # Yield an initial ping/comment to force headers to be sent immediately
        yield ": ping\n\n"
        
        # Then yield the actual response stream
        async for chunk in _chat_stream(request.prompt, request.session_id):
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


# Mount the entire static directory to root to serve index.html and all public assets (e.g. images)
# We place this AFTER API routes so they take precedence.
# html=True means it serves index.html for root /.
# Static file serving logic
# 1. Try local dev build (super-web/dist) relative to project root

dev_dist_dir = project_root / "super-web" / "dist"
static_dir = Path(__file__).parent / "static"

if dev_dist_dir.exists():
    logger.info(f"Serving static files from local build: {dev_dist_dir}")
    app.mount("/", StaticFiles(directory=dev_dist_dir, html=True), name="static")
elif static_dir.exists():
    logger.info(f"Serving static files from internal static dir: {static_dir}")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning("No static files found. Frontend will not be available.")


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
