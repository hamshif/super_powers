#!/bin/bash
set -e

# Ensure we are in project root (where this script should be run from generally, but let's be safe)
cd "$(dirname "$0")"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install "ray[default]" "pydantic>=2.0" langchain langchain-openai uvicorn fastapi nest_asyncio httpx pandas thefuzz pyspark==4.0.1 pyhocon networkx pyvis openpyxl python-dotenv rich
else
    source .venv/bin/activate
fi

# Ensure frontend is built
if [ ! -d "super-web/dist" ]; then
    echo "Building frontend..."
    cd super-web
    npm install
    npm run build
    cd ..
fi

echo "Starting Super Power Sage (Local)..."
export PYTHONPATH=$PYTHONPATH:$(pwd)/super-services/src

# Run with uvicorn directly
python3 super-services/src/super/apps/super_power_sage/super_power_sage.py
