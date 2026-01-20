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
from fastapi import FastAPI, HTTPException
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
    global _graph
    
    conf = get_app_conf(app="super_power_sage")
    level = conf.get_string("super_power_sage.logging.level", "INFO")
    _apply_log_level(level)
    logger.info("Super Power Sage starting up...")
    
    # 1. Initialize Ray and Actor
    try:
        import ray
        from super.apps.generate_powers.worker import HeroGenerator
        from super.apps.super_power_sage import state
        
        # Init Ray (auto-detects existing cluster or starts local)
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
            
        logger.info("Ray Initialized.")
        
        # Start Actor
        # Use a named actor if we want to ensure only one exists, or just create one.
        # For simplicity in this app, we create one instance for the app lifespan.
        state.hero_generator = HeroGenerator.remote()
        logger.info("HeroGenerator Actor started and registered in state.")
        
    except ImportError as e:
        logger.warning(f"Ray/HeroGenerator dependencies not found. Asynchronous generation will fail: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize Ray Actor: {e}", exc_info=True)

    # 2. Init Agent
    # Uses robust initialization with active rate-limit check and fallback
    try:
        model = utils.get_valid_llm(model_name="gpt-3.5-turbo")
    except (RuntimeError, ValueError) as e:
        logger.error(f"Failed to initialize Agent Model (Quota/Key issue): {e}")
        logger.warning("STARTING IN MOCK/OFFLINE MODE. Chat will fail until valid keys are provided.")
        # Fallback to a dummy model so the server starts. 
        # Runtime calls will fail gracefully in the chat stream.
        model = ChatOpenAI(api_key="sk-mock-key-to-allow-startup", model="gpt-3.5-turbo")
    checkpointer = MemorySaver()

    # Dependency Injection: Inject OpenAI model
    _graph = SageGraphFactory.create_graph(model, checkpointer=checkpointer)
    logger.info("Agent graph initialized with persistence.")
    
    yield
    
    # Shutdown logic
    logger.info("Super Power Sage shutting down...")
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
        
        while True:
            # Drain the queue for HERO_DATA events
            while state.data_queue:
                data_item = state.data_queue.pop(0)
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
async def visualize_graph(center: str | None = None):
    """
    Returns an HTML visualization of the graph.
    If 'center' is provided, shows subgraph around that node.
    If 'center' is None/Empty, shows the High-Level Overview.
    """
    try:
        # Lazy import or get global GM if available. 
        # Using tools._get_gm() pattern or re-instantiating.
        # Ideally we share the instance. In server.py we can load it once. 
        # But for now, let's instantiate to be safe and stateless or check global _graph's tools?
        # To avoid overhead, let's use a cached global variable in this module if possible, 
        # OR just instantiate since it reads parquet (via Pandas) which is cached by OS.
        
        # We need the warehouse path.
        # Assuming defaults work in GraphManager logic (which we verified uses env or relative path).
        from super.core.graph import GraphManager
        
        # Optimization: Instantiate once globally? 
        # For this iteration, let's instantiate.
        # If warehouse loading is slow (~1-2s), this endpoint might be slow on first hit.
        
        # Explicitly pass the warehouse path to ensure it works regardless of CWD
        warehouse_path = project_root / "data/warehouse"
        gm = GraphManager(warehouse_root=str(warehouse_path)) 
        
        if center and center.strip() and center.lower() != "overview":
            # Contextual Subgraph
            sub_G = gm.subgraph_for_hero(center, depth=2)
            if not sub_G or sub_G.number_of_nodes() == 0:
                # Fallback if hero not found (maybe it's a seed or power?)
                # Try getting subgraph for any node ID
                sub_G = gm.get_subgraph_for_node(center, depth=2) # Returns dict, visualize needs Graph
                # Wait, get_subgraph_for_node returned serialization dict.
                # Use subgraph logic directly:
                if center in gm.G:
                     # Create subgraph manually using nx
                     # Re-use logic or just accept it might be empty
                     nodes = {center} | set(gm.G.neighbors(center))
                     sub_G = gm.G.subgraph(nodes)
                else:
                     return HTMLResponse(f"<h3>Node '{center}' not found in graph.</h3>")
        else:
            # Overview Mode
            sub_G = gm.get_overview_graph(limit=150)
            
        html_content = gm.visualize(sub_G, filename=None)
        return HTMLResponse(content=html_content, status_code=200)
        
    except Exception as e:
        logger.error(f"Graph viz failed: {e}", exc_info=True)
        return HTMLResponse(f"<h3>Error generating graph: {e}</h3>", status_code=500)


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
