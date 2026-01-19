
#!/bin/bash
set -euo pipefail

echo "Starting Super Powers Container..."
echo "Mapping Host Port 8000 -> Container Port 8000"
echo "Access at: http://localhost:8000/docs"

# Run the container
# -it: Interactive (Ctrl+C to stop)
# --rm: Remove container after exit (keep things clean)
# -p 8000:8000: Map server port
docker run -it --rm -p 8000:8000 super_powers:latest
