
#!/bin/bash
set -euo pipefail

echo "Starting Super Powers Container..."
echo "Mapping Host Port 8000 -> Container Port 8000"
echo "Access at: http://localhost:8000/docs"

# Check for .env file
ENV_ARGS=""
if [ -f ".env" ]; then
    echo "Loading .env file..."
    ENV_ARGS="--env-file .env"
fi

# Run the container
# -it: Interactive
# --rm: Cleanup
# -p 8000:8000: Port map
# -e OPENAI_API_KEY: Pass key from host if set (overrides .env if passed explicitly)
docker run -it --rm -p 8000:8000 $ENV_ARGS -e OPENAI_API_KEY super_powers:latest
