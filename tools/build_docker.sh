
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

# 3. Copy Dockerfile
# We move the Dockerfile to the root of the context
echo "Copying Dockerfile..."
cp "${PROJECT_ROOT}/tools/Dockerfile" "${STAGE_DIR}/Dockerfile"

# 4. Build Docker Image
echo "Building Image (super_powers:latest)..."
cd "${STAGE_DIR}"
docker build -t super_powers:latest .

echo "=== Build Complete ==="
echo "Run with: docker run -it super_powers:latest"
