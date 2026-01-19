
#!/bin/bash
set -e

echo "============================================"
echo "   🦸 Super Powers Sage: Reviewer Demo   "
echo "============================================"

# Ensure we are in project root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo ""
echo "🚀 [Step 1/3] Packaging Data..."
# Uses standard library only, safe to run with system python3
python3 tools/zip_data.py

echo ""
echo "🐳 [Step 2/3] Building Docker Environment..."
bash tools/build_docker.sh

echo ""
echo "✨ [Step 3/3] Launching App..."
echo "The app will accept connections at http://localhost:8000"

# Try to open browser
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8000 >/dev/null 2>&1 &
elif command -v open > /dev/null; then
    open http://localhost:8000 >/dev/null 2>&1 &
fi

bash tools/run_docker.sh
