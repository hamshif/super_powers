
import subprocess
import time
import requests
import sys
import os
from pathlib import Path

# Config
BASE_URL = "http://127.0.0.1:8000"
SERVER_SCRIPT = "super-services/src/super/apps/super_power_sage/super_power_sage.py"
PYTHON_EXE = "/home/gideon/tmp/super_powers/.venv/bin/python3"
CWD = "/home/gideon/tmp/super_powers"

def wait_for_server(timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=1)
            if resp.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    return False

def test_graph_endpoint():
    print(f"Testing Graph Endpoint...")
    try:
        # Request Overview (should hit GraphService Actor)
        resp = requests.get(f"{BASE_URL}/super_powers_sage/visualize_graph?center=overview", timeout=10)
        if resp.status_code == 200:
            print("SUCCESS: Endpoint returned 200 OK")
            if "<html" in resp.text.lower() or "<!doctype html>" in resp.text.lower():
                print("SUCCESS: Content looks like HTML")
                return True
            else:
                print("FAILURE: Content is not HTML")
                print(resp.text[:200])
        else:
            print(f"FAILURE: Status Code {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"FAILURE: Exception {e}")
    return False

def main():
    print("Starting Server...")
    # Start server in background
    proc = subprocess.Popen(
        [PYTHON_EXE, SERVER_SCRIPT],
        cwd=CWD,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        if wait_for_server():
            print("Server is UP.")
            success = test_graph_endpoint()
            if success:
                print("TEST PASSED")
                sys.exit(0)
            else:
                print("TEST FAILED")
                sys.exit(1)
        else:
            print("Server failed to start (timeout).")
            # Print stderr
            _, stderr = proc.communicate(timeout=5)
            print("STDERR:", stderr)
            sys.exit(1)
    finally:
        print("Killing Server...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
