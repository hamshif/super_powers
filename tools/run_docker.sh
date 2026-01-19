
#!/bin/bash
set -euo pipefail

echo "Starting Super Powers Container..."
echo "Mapping Host Port 8000 -> Container Port 8000"
echo "Access at: http://localhost:8000/docs"

# Check for .env file and sanitize it for Docker (Docker expects KEY=VAL, not KEY: VAL)
ENV_ARGS=""
if [ -f ".env" ]; then
    echo "Loading .env file..."
    # Create a compatible temp env file
    # 1. Remove leading/trailing whitespace
    # 2. Replace first ": " with "=" (handles YAML/JSON-like format)
    # 3. Filter out lines without keys
    grep -v '^#' .env | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/:[[:space:]]*/=/' > .env.docker
    ENV_ARGS="--env-file .env.docker"
fi

# Run the container
# -it: Interactive
# --rm: Cleanup
# -p 8000:8000: Port map
# -e OPENAI_API_KEY: Pass key from host if set (overrides .env if passed explicitly)
docker run -d \
    --name $CONTAINER_NAME \
    --network host \
    --shm-size=2g \
    -e OPENAI_API_KEY=$OPENAI_API_KEY \
    -e TAVILY_API_KEY=$TAVILY_API_KEY \
    -v $(pwd)/super-services/src:/app/src \
    $IMAGE_NAME

# Cleanup temp file
[ -f ".env.docker" ] && rm .env.docker
