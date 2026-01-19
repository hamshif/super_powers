
#!/bin/bash
set -euo pipefail

echo "Starting Super Powers Container..."
echo "Mapping Host Port 8000 -> Container Port 8000"
echo "Access at: http://localhost:8000/docs"

# Defaults
CONTAINER_NAME="${CONTAINER_NAME:-super_powers_container}"
IMAGE_NAME="${IMAGE_NAME:-super_powers:latest}"

# Check for .env file and sanitize it for Docker (Docker expects KEY=VAL, not KEY: VAL)
ENV_ARGS=""
if [ -f ".env" ]; then
    echo "Loading .env file..."
    # Create a compatible temp env file
    grep -v '^#' .env | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/:[[:space:]]*/=/' > .env.docker
    ENV_ARGS="--env-file .env.docker"
fi

# Cleanup existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container: $CONTAINER_NAME"
    docker rm -f "$CONTAINER_NAME"
fi

# Build Docker Arguments
DOCKER_OPTS=(
    -d
    --name "$CONTAINER_NAME"
    -p 8000:8000
    --shm-size=2g
    -v "$(pwd)/super-services/src:/app/src"
)

# Only inject API keys from shell if they are actually set
# This prevents overwriting .env values with empty strings
if [ -n "${OPENAI_API_KEY:-}" ]; then
    DOCKER_OPTS+=(-e "OPENAI_API_KEY=${OPENAI_API_KEY}")
fi

if [ -n "${TAVILY_API_KEY:-}" ]; then
    DOCKER_OPTS+=(-e "TAVILY_API_KEY=${TAVILY_API_KEY}")
fi

# Run the container
docker run "${DOCKER_OPTS[@]}" $ENV_ARGS "$IMAGE_NAME"

# Cleanup temp file
[ -f ".env.docker" ] && rm .env.docker

echo "Container started. Tailing logs (Ctrl+C to stop viewing, container continues running)..."
exec docker logs -f "$CONTAINER_NAME"
