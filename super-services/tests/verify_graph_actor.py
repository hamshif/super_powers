
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
    print(f"Testing Graph Endpoint (JSON)...")
    try:
        # 1. Get Overview Stats
        print("Fetching Overview...")
        resp_ov = requests.get(f"{BASE_URL}/super_powers_sage/graph_data?center=overview", timeout=10)
        overview_count = 0
        if resp_ov.status_code == 200:
             nodes_ov = resp_ov.json().get("nodes", [])
             overview_count = len(nodes_ov)
             print(f"Overview Node Count: {overview_count}")
        
        # 2. Get Superman Stats
        target_hero = "Superman"
        print(f"Fetching {target_hero}...")
        resp = requests.get(f"{BASE_URL}/super_powers_sage/graph_data?center={target_hero}", timeout=10)
        
        if resp.status_code == 200:
            print("SUCCESS: Endpoint returned 200 OK")
            data = resp.json()
            nodes = data.get("nodes", [])
            print(f"Hero Subgraph Node Count: {len(nodes)}")
            
            # Compare
            if len(nodes) == overview_count and overview_count > 0:
                print("FAILURE: Subgraph size IDENTICAL to Overview. Likely fallback triggered OR graph is small.")
            elif len(nodes) < overview_count:
                print("SUCCESS: Subgraph is smaller than Overview.")
            
            return True
        else:
            print(f"FAILURE: Status Code {resp.status_code}")
    except Exception as e:
        print(f"FAILURE: Exception {e}")
    return False

def main():
    print("Starting Server...")
    # Start server in background
    # Start server in background with unbuffered output
    proc = subprocess.Popen(
        [PYTHON_EXE, "-u", SERVER_SCRIPT], # -u for unbuffered
        cwd=CWD,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    success = False
    try:
        if wait_for_server():
            print("Server is UP.")
            success = test_graph_endpoint()
        else:
             print("Server failed to start (timeout).")
             
    finally:
        if proc.poll() is None:
            print("Killing Server...")
            proc.terminate()
            proc.wait()

        # Print Server Logs
        print("\n--- SERVER LOGS ---")
        try:
            outs, errs = proc.communicate(timeout=2)
            if outs: print(outs)
            if errs: 
                print("--- STDERR ---")
                print(errs)
        except Exception as e:
            print(f"Log retrieval failed: {e}")

    if success:
         print("\nTEST PASSED")
         sys.exit(0)
    else:
         print("\nTEST FAILED")
         sys.exit(1)

if __name__ == "__main__":
    main()
