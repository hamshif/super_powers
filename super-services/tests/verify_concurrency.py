
import subprocess
import time
import requests
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

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
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False

def make_request(url, name):
    start = time.time()
    try:
        resp = requests.get(url, timeout=10)
        duration = time.time() - start
        print(f"{name}: Finished in {duration:.4f}s (Status: {resp.status_code}, Size: {len(resp.content)} bytes)")
        return duration
    except Exception as e:
        print(f"{name}: Failed {e}")
        return 999.0

def test_concurrency():
    print("Testing Concurrency (Blocking vs Non-Blocking)...")
    
    # 1. Warm up actor
    requests.get(f"{BASE_URL}/super_powers_sage/visualize_graph?center=overview")
    
    # 2. Launch Slow Request (Graph) and Fast Request (Health) in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Start Graph request (should take > 0.1s due to processing/network overhead or intentional work)
        # Note: Since it's now async, the request *handling* on main thread is fast, 
        # but the *response* blocks the client until Actor finishes.
        # Ideally, we check if Health Ping is blocked.
        
        future_graph = executor.submit(make_request, f"{BASE_URL}/super_powers_sage/visualize_graph?center=overview", "GraphRequest")
        
        # Small delay to ensure Graph request hit the server first (simulating race)
        time.sleep(0.05) 
        
        future_health = executor.submit(make_request, f"{BASE_URL}/health", "HealthPing")
        
        graph_time = future_graph.result()
        health_time = future_health.result()
        
    print(f"\nResults:")
    print(f"Graph Time: {graph_time:.4f}s")
    print(f"Health Time: {health_time:.4f}s")
    
    # Assertion: Health Ping should satisfy < 0.2s even if Graph takes longer
    # If blocking, Health Ping would queue behind Graph processing (0.4s+).
    if health_time < 0.2:
        print("SUCCESS: Health Check was fast (Non-Blocking).")
        return True
    else:
        print("FAILURE: Health Check was slow (Blocked?).")
        return False

def main():
    print("Starting Server...")
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
            success = test_concurrency()
            if success:
                print("TEST PASSED")
                sys.exit(0)
            else:
                print("TEST FAILED")
                sys.exit(1)
        else:
            print("Server failed to start.")
            _, stderr = proc.communicate(timeout=5)
            print(stderr)
            sys.exit(1)
    finally:
        print("Killing Server...")
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
