
#!/bin/bash
set -e

echo "=== Super Power Sage Container ==="
echo "Starting Server..."

# Ensure the installed package or source is in path
# Although 'pip install -e' should handle it, explicit PYTHONPATH is safer in some container contexts
export PYTHONPATH="${PYTHONPATH}:/app/super-services/src"

# Run Uvicorn
# We force 0.0.0.0 to allow access from outside the container
exec uvicorn super.apps.super_power_sage.super_power_sage:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
