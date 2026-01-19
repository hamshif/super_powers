
#!/bin/bash
set -euo pipefail

# Find project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STAGE_DIR="${PROJECT_ROOT}/stage/docker_context"

echo "=== Building Docker Image ==="
echo "Project Root: ${PROJECT_ROOT}"
echo "Stage Dir:    ${STAGE_DIR}"

# 1. Prepare Stage Directory
if [ -d "${STAGE_DIR}" ]; then
    echo "Cleaning stage directory..."
    rm -rf "${STAGE_DIR}"
fi
mkdir -p "${STAGE_DIR}"

# 2. Clone Repository (Clean State)
# We clone the local directory ($PROJECT_ROOT) into the stage dir
echo "Cloning local repository..."
git clone "${PROJECT_ROOT}" "${STAGE_DIR}"

# 3. Inject Data Zip
# Find the latest data zip in project root using strict regex pattern
# Pattern: data_<numeric>kb_<hex>.zip (e.g., data_1794kb_a11b4f9.zip)
# We use 'find' with posix-extended regex, sort by modification time reversed (newest first).
LATEST_ZIP=$(find "${PROJECT_ROOT}" -maxdepth 1 -regextype posix-extended -regex ".*/data_[0-9]+kb_[a-f0-9]+\.zip" -printf "%T@ %p\n" | sort -rn | head -n1 | cut -d' ' -f2-)

if [ -z "${LATEST_ZIP}" ]; then
    echo "ERROR: No data zip found matching regex 'data_[0-9]+kb_[a-f0-9]+.zip'. Cannot build."
    exit 1
fi

echo "Injecting Data: $(basename "${LATEST_ZIP}") -> data.zip"
cp "${LATEST_ZIP}" "${STAGE_DIR}/data.zip"

# 4. Copy Dockerfile
# We move the Dockerfile to the root of the context
echo "Copying Dockerfile..."
cp "${PROJECT_ROOT}/tools/Dockerfile" "${STAGE_DIR}/Dockerfile"

# 5. Build Docker Image
echo "Building Image (super_powers:latest)..."
cd "${STAGE_DIR}"
docker build -t super_powers:latest .

echo "=== Build Complete ==="
echo "Run with: docker run -it super_powers:latest"
