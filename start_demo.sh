
#!/bin/bash
set -e

echo "============================================"
echo "   🦸 Super Powers Sage: Reviewer Demo   "
echo "============================================"

# Ensure we are in project root (where this script lives)
# Ensure we are in project root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
# Implement cross-platform browser opening
url="http://localhost:8000"
echo "Opening $url in your default browser..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$url"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash, etc.)
    start "$url"
elif grep -q Microsoft /proc/version 2>/dev/null; then
    # WSL (Windows Subsystem for Linux)
    if command -v wslview >/dev/null; then
        wslview "$url" 
    else
        explorer.exe "$url" 
    fi
elif command -v xdg-open > /dev/null; then
    # Linux (Standard)
    xdg-open "$url" >/dev/null 2>&1 &
else
    echo "Could not detect default browser. Please open $url manually."
fi

bash tools/run_docker.sh
