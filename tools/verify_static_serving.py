
import os
import sys
from fastapi.testclient import TestClient

# Ensure src is on path
sys.path.append(os.path.abspath("super-services/src"))

from super.apps.super_power_sage.super_power_sage import app

def test_static_serving():
    client = TestClient(app)
    response = client.get("/")
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success: GET / returned 200 OK")
        if "<html" in response.text.lower() or "doctype html" in response.text.lower():
             print("Success: Response contains HTML content.")
        else:
             print("Warning: Response content does not look like HTML.")
             print(response.text[:200])
    else:
        print(f"Failure: {response.text}")
        exit(1)

if __name__ == "__main__":
    test_static_serving()
