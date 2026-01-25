# Agent Long Term Guidelines
Adhere to these guidelines for all tasks. Compile these into long term lating intents and in all contexts and subagents.
-
## 1. Version Control
- **Commits**: Do not create git commits without explicit user permission.

## 2. Configuration Standards
- **Strict Loading**: When using configuration helpers (e.g., `get_project_conf`, `get_app_conf`), **NEVER** supply fallbacks or try catch wrappers! using `project_root`, `stage_root` to retain a strict single source of truth.
- **Explicit Failure**: If a required configuration root or file is absent, the application MUST crash or raise an explicit error immediately. Silent defaults hide deployment issues.
- **Environment Compliance**: Minimize & Respect the use of environment variables `.env` and environment variables as the source of truth for credentials and paths.
- **Temporary Scripts**: If creating scripts for debugging, testing, or temporary utility, place them in a `tmp-scripts/` directory at the project root.

## 3. Planning
- **Questions**: When user asks questions answer them and stop to verify alignment before proceeding.
- **Large Plans**: When formulating large plans, break them down into smaller tasks and verify alignment before proceeding. 

# Python
- **Running Python Code**: always use super pyenv to run python code, never add inline adding of source to path. top level package_py will install every dependency needed, by calling module level dependency package_py scripts. If your sandbox prohibits prolonged pyenv activation, use pyenv path variable before the command to set the path to the python interpreter.

## 4. File Organization
- **Backends**: Backend related code in python should be placed in `super-services/`.
- **Frontends**: Frontend related code in python should be placed in `super-web/`.
- **Data and Notebooks**: Unless otherwise specified, Jupyter notebooks should be placed in `super-explore/`. Never create `notebooks/` directories inside service modules (e.g., `super-services/`).

## 5. Concurrency & Performance
- **Thread & Process Safety**: Non-Blocking tools executed by agents must NOT block the main thread.
    - Use `async/await` for native async operations (e.g., LLM calls).
    - Offload blocking I/O or CPU tasks (e.g., Pandas ETL) to an executor (`loop.run_in_executor`).


## 6. Testing Standards
- **Local First**: You must run and verify the application locally (python/node) and produce success logs *before* creating or building any Docker images.
    - **Workflow**: Local Code -> Local Run (Verify Logs) -> Docker Build.
    - **Forbidden**: Do not propose building Docker images until local verification is complete.

## 7. Temporary Scripting
- **Location**: All temporary, debugging, or reproduction scripts must be placed in `tmp-scripts/`.
- **Git Ignore**: Verify `tmp-scripts/` is in `.gitignore`.
- **Cleanup**: Delete scripts when no longer needed or promote them to proper tests.
