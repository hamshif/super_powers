
#!/bin/bash
set -euo pipefail

# Find project root
# Find project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
# Standardized Name: data.zip
ZIP_PATH="${PROJECT_ROOT}/data.zip"

if [ ! -f "${ZIP_PATH}" ]; then
    echo "ERROR: ${ZIP_PATH} not found. Please run 'python3 tools/zip_data.py' first."
    exit 1
fi

echo "Injecting Data: Unzipping to stage..."
# Unzip directly into the stage directory
# -q: quiet
# -o: overwrite
# -d: destination
unzip -q -o "${ZIP_PATH}" -d "${STAGE_DIR}"

# Remove the zip file from stage if it was copied or if unzip left artifacts? 
# Wait, unzip -d puts the CONTENTS into STAGE_DIR.
# If data.zip contains a 'data/' folder, then STAGE_DIR/data will exist.
# We DO NOT want the .zip file itself in the docker build context if we are providing the unzipped version.
# Since we unzipped FROM source TO stage, the zip isn't in stage unless we put it there.
# Previous code did: cp "${ZIP_PATH}" "${STAGE_DIR}/data.zip"
# We are REPLACING that. So we just unzip.


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
