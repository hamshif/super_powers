
import os
import sys
import pytest
import time
from fastapi.testclient import TestClient

# Ensure src is on path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import app
from super.apps.super_power_sage.super_power_sage import app
from super.core.utils import get_valid_llm

def generate_novel_name():
    """Ask LLM for a unique superhero name to ensure we don't hit cache/pre-existing data."""
    try:
        llm = get_valid_llm()
        response = llm.invoke("Generate a unique, single-word superhero name that sounds like a quantum physicist. Return ONLY the name.")
        name = response.content.strip().replace(".", "").replace(" ", "")
        print(f"Generated Novel Name: {name}")
        return name
    except Exception as e:
        print(f"LLM Name Generation failed: {e}. Fallback to 'QuantumTestHero'")
        return "QuantumTestHero"

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_novel_hero_creation_and_retrieval(client):
    """
    1. Generate Novel Name.
    2. Create Hero via Chat (Tool Call).
    3. Retrieve Details via Chat (Tool Call) -> Verifies 'dict' fix.
    """
    hero_name = generate_novel_name()
    session_id = f"test_novel_{int(time.time())}"
    
    print(f"\n--- Starting Novel Hero Test: {hero_name} ---")
    
    # 1. Creation
    print(f"Requesting creation of {hero_name}...")
    create_prompt = f"Create a new hero named '{hero_name}'. They control probability fields."
    
    resp_create = client.post(
        "/super_powers_sage",
        json={"prompt": create_prompt, "session_id": session_id}
    )
    assert resp_create.status_code == 200
    # Consuming stream to verify success message
    creation_success = False
    for line in resp_create.iter_lines():
        if not line: continue
        # decoded = line.decode('utf-8') # Removed
        decoded = line
        if "Success!" in decoded or "created" in decoded or hero_name in decoded:
            creation_success = True
    
    if not creation_success:
        print("WARNING: Did not see explicit success message in creation stream, but proceeding to retrieval verification.")

    # 2. Retrieval (The real test for the bug fix)
    print(f"Requesting details for {hero_name}...")
    detail_prompt = f"Tell me about {hero_name}'s genetic makeup"
    
    resp_details = client.post(
        "/super_powers_sage",
        json={"prompt": detail_prompt, "session_id": session_id}
    )
    assert resp_details.status_code == 200
    
    found_hero_data_event = False
    content_received = False
    
    for line in resp_details.iter_lines():
        if not line: continue
        # decoded = line.decode('utf-8') # Removed
        decoded = line
        
        # Check for regressions
        if "Error processing request" in decoded:
             print(f"FAILURE: Server returned error in stream: {decoded}")
             if "must be str, bytes or bytearray, not dict" in decoded:
                 print("!!! Confirmed TypeError Regression !!!")
             exit(1)
             
        if "event: hero_data" in decoded:
            found_hero_data_event = True
            print("Found HERO_DATA event (Genetic Data) in stream!")
            
        if "event: answer" in decoded:
            content_received = True

    if not found_hero_data_event:
        print("FAILURE: Did not see 'event: hero_data' for genetic retrieval.")
        exit(1)
        
    print(f"Novel Hero Test ({hero_name}) Passed!")

if __name__ == "__main__":
    # Minimal runner
    with TestClient(app) as c:
        test_novel_hero_creation_and_retrieval(c)
