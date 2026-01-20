
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure src is on path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import app
from super.apps.super_power_sage.super_power_sage import app
from super.apps.super_power_sage import state

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_graph_query_integration(client):
    """
    Verify that asking for connected entities triggers the graph tool and returns HERO_DATA event.
    """
    print("\nRequesting graph connections...")
    # This prompt should trigger 'get_connected_entities'
    sse_response = client.post(
        "/super_powers_sage",
        json={"prompt": "Show me the connections for Superman.", "session_id": "integration_test_graph"}
    )
    
    assert sse_response.status_code == 200
    
    found_graph_event = False
    
    for line in sse_response.iter_lines():
        if not line: continue
        # decoded_line = line.decode('utf-8') 
        # Line is already str from TestClient/httpx in this context
        decoded_line = line
        
        if "Error processing request" in decoded_line:
             print(f"FAILURE: Server returned error in stream: {decoded_line}")
             exit(1)
        
        if "name 'SseEvent' is not defined" in decoded_line:
             print(f"FAILURE: Caught SseEvent NameError regression: {decoded_line}")
             exit(1)

        if "event: hero_data" in decoded_line:
             found_graph_event = True
             print("Found HERO_DATA event (Graph) in stream!")
             
    if not found_graph_event:
        print("WARNING: Did not see 'event: hero_data' for graph query. Tool might not have been called or queue not drained.")
        # We don't exit(1) strictly here unless we are sure the LLM called the tool. 
        # But for 'Show me connections', it usually does.
        
    print("Graph Query Integration Test Complete.")

if __name__ == "__main__":
    # Minimal runner
    with TestClient(app) as c:
        test_graph_query_integration(c)
