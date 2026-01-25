
#!/bin/bash
set -e

echo "============================================"
echo "   🦸 Super Powers Sage: Reviewer Demo   "
echo "============================================"

# Ensure we are in project root (where this script lives)
# Ensure we are in project root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"


# 2. Configuration
# Allow overriding the pyenv name (default: super)
PROJECT_PYENV="${PROJECT_PYENV:-super}"
PYTHON_VERSION="3.11.11" # Target python version for env creation

echo ""
echo "🔧 [Step 1/4] Environment Setup..."
echo "Target Pyenv: '${PROJECT_PYENV}'"

# Check if pyenv is installed
if ! command -v pyenv >/dev/null 2>&1; then
    echo "❌ Error: 'pyenv' is not installed or not on PATH."
    echo "Please install pyenv first: https://github.com/pyenv/pyenv#installation"
    exit 1
fi

# Check/Create Virtualenv
if pyenv virtualenvs --bare | grep -q "^${PROJECT_PYENV}$"; then
    echo "✅ Virtualenv '${PROJECT_PYENV}' exists."
else
    echo "⚡ Virtualenv '${PROJECT_PYENV}' missing. Creating..."
    # Ensure the python version is installed
    if ! pyenv versions --bare | grep -q "^${PYTHON_VERSION}"; then
         echo "Installing Python ${PYTHON_VERSION}..."
         pyenv install "${PYTHON_VERSION}"
    fi
    pyenv virtualenv "${PYTHON_VERSION}" "${PROJECT_PYENV}"
fi

# Resolve Python Path dynamically
PYENV_ROOT="$(pyenv root)"
PROJECT_PYTHON="${PYENV_ROOT}/versions/${PROJECT_PYENV}/bin/python"

if [[ ! -x "${PROJECT_PYTHON}" ]]; then
    echo "❌ Error: Python executable not found at ${PROJECT_PYTHON}"
    exit 1
fi

echo "✅ Using Python: ${PROJECT_PYTHON}"

echo ""
echo "📦 [Step 2/4] Dependencies..."
# Run package_py.sh using the target environment
PYENV_VERSION="${PROJECT_PYENV}" bash package_py.sh

echo ""
echo "📂 [Step 3/4] Data Setup..."
DATA_DIR="${SCRIPT_DIR}/data"
# Use single brackets for sh compatibility or rely on shebang being bash
# The script is usually run with ./start_demo.sh which uses shebang #!/bin/bash
# But output said "[[ not found" which implies it ran with /bin/sh ?
# Ah, I replaced the content but maybe I lost the shebang or it was run with 'sh start_demo.sh'?
# The command was "./start_demo.sh". If shebang is #!/bin/bash it should be fine.
# Let's be robust.

if [ -d "${DATA_DIR}" ] && [ "$(ls -A "${DATA_DIR}")" ]; then
    echo "✅ 'data/' directory exists and is not empty. Skipping unzip."
else
    # Check for data.zip in SCRIPT_DIR
    if [ -f "${SCRIPT_DIR}/data.zip" ]; then
        echo "⚡ Unzipping data.zip to data/..."
        # unzip needs explicit path
        unzip -q -o "${SCRIPT_DIR}/data.zip" -d "${SCRIPT_DIR}"
    else
        echo "⚠️ Warning: data.zip not found at ${SCRIPT_DIR}/data.zip (and data/ is empty)." 
    fi
fi

echo ""
echo "✨ [Step 4/4] Launching App..."
echo "The app will accept connections at http://localhost:8000"

# Try to open browser (background)
url="http://localhost:8000"
(
    sleep 3 # Give server a moment to start
    case "$OSTYPE" in
      darwin*) open "$url" ;;
      cygwin*|msys*|win32*) start "$url" ;;
      *) 
        if grep -q Microsoft /proc/version 2>/dev/null; then
            if command -v wslview >/dev/null; then wslview "$url"; else explorer.exe "$url"; fi
        elif command -v xdg-open >/dev/null; then
            xdg-open "$url" >/dev/null 2>&1
        fi
        ;;
    esac
) &

# Launch Server using Explicit Python from the Environment
# We use the 'run_local.sh' logic but inline or via python -m
# The original script called run_docker.sh, but the user wants to run locally/easily?
# Wait, the original script said:
#   bash tools/zip_data.py
#   bash tools/build_docker.sh
#   bash tools/run_docker.sh
#
# BUT the user said "ignoring data.zip causes trouble for others to pack and run dockers easily".
#
# IF the intent is truly to run DOCKER, then my python env setup is for what?
# "We also need to assume they don't have a pyenv activated when they run it, so we need to get or create and activate."
#
# Ah, the `zip_data.py` needs python. And potentially other tools.
# If the goal is running Docker, we still need python for the preparatory scripts?
#
# Re-reading: "run dockers easily using start_demo.sh"
#
# So the MAIN GOAL is likely running the Docker container.
# BUT `zip_data.py` (line 17 original) ran with `python3`.
# So we are replacing the PRE-DOCKER setup environment.
#
# Original lines 20-21: build_docker.sh
# Original lines 63: run_docker.sh
# Use those.

echo "🐳 Building Docker..."
bash tools/build_docker.sh

echo "🚀 Running Docker..."
bash tools/run_docker.sh

