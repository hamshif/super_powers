Version Control
==

Agents will not make commits without explicit permission.

Configuration
==

When using configuration loading helpers, do not supply fallback defaults for missing config roots or files; failures should be explicit if configuration is absent.

Codex Sandbox
==

Codex runs with workspace-only write permissions, so it cannot modify files outside `/home/gideon/tmp/super_powers` (e.g., `~/.pyenv`). Operations that require writing there must be performed by the user or with an escalated command request.

Tool Implementation & Concurrency
==

Tools executed by agents (especially in async event loops like FastAPI/LangGraph) must NOT block the main thread.
1.  **Async/Await**: Native async code should be used whenever possible (e.g., `ainvoke` for LLMs).
2.  **Thread Safety**: Blocking I/O or CPU-intensive tasks (like ETL or Pandas writes) must be offloaded to an executor (e.g., `loop.run_in_executor`).
3.  **Process Safety**: Shared resources (like database connections or graphs) must be process-safe or initialized per-request if not designed for concurrency.

**Example**: The `Super Power Sage` tools (`src/super/apps/super_power_sage/tools.py`) strictly follow these rules, using `ThreadPoolExecutor` for the `ad_hoc.py` Pandas ETL to prevent blocking the FastAPI event loop.
