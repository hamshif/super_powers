
import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Ensure src is on path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../super-services/src"))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import app
from super.apps.super_power_sage.super_power_sage import app
from super.apps.super_power_sage import state

# Mock expensive external dependencies
# We want to test the FLOW: App Init -> Ray Init -> Tool Call -> Actor Call -> Response.

@pytest.fixture
def client():
    # Use TestClient as context manager to trigger lifespan
    with TestClient(app) as c:
        yield c

def test_ray_initialization(client):
    """
    Verify that Ray is initialized and the Actor is registered in state.
    """
    assert state.hero_generator is not None, "HeroGenerator Actor should be initialized in state"

def test_create_hero_tool_integration(client):
    """
    Verify that calling create_new_hero tool submits to the Actor correctly.
    Since we don't have a real Ray cluster in the test environment potentially,
    we rely on 'ray[default]' being installed and working locally.
    """
    # 4. Verify Generation
    # Use the /super_powers_sage endpoint to simulate a real user request
    sse_response_creation = client.post(
        "/super_powers_sage",
        json={"prompt": "Create a new hero named 'StreamTestHero' who is a master of liquid data.", "session_id": "integration_test"}
    )
    assert sse_response_creation.status_code == 200
    
    # We expect this to succeed and generate the hero.
    # Now, Step 5: Verify Side-Channel retrieval
    print("Creation request sent. Now requesting details to trigger Side-Channel...")
    
    sse_response_details = client.post(
        "/super_powers_sage",
        json={"prompt": "Fetch the full genetic details of StreamTestHero.", "session_id": "integration_test"}
    )
    
    found_hero_data = False
    
    for line in sse_response_details.iter_lines():
        if not line: continue
        decoded_line = line.decode('utf-8')
        
        # Check for errors in the stream
        if "Error processing request" in decoded_line:
             print(f"FAILURE: Server returned error in stream: {decoded_line}")
             exit(1)
        
        if "event: hero_data" in decoded_line:
            found_hero_data = True
            print("Found HERO_DATA event in stream!")
            # Do NOT break here. Continue consuming stream to ensure no subsequent errors occur.
            
    if not found_hero_data:
        print("FAILURE: Did not see 'event: hero_data' in the details response.")
        # Print valid lines to see what happened
        # (Commented out to avoid log spam, but helpful for debugging)
        # print(sse_response_details.text[:500])
        exit(1)
        
    print("Integration Test Complete: Ray Actor + Side-Channel Stream verified.")
    
    from super.apps.super_power_sage.tools import create_new_hero
    
    # We need to mock the Actor's remote method to avoid actual long-running generation 
    # but verify the connection.
    # If Ray is running, we can let it run.
    
    # But for a fast check, we can verify the state linkage.
    assert state.hero_generator is not None
    
    # If we want to test true integration, we need to call the tool.
    # But calling the tool requires asyncio loop which TestClient manages? 
    # Tools are async.
    
    import asyncio
    
    # We'll patch the 'remote' call on the actor handle to verify call only?
    # No, user said "suggest you didn't test the server". Implies runtime failure.
    # So we should trust the real actor.
    
    # Let's try to run the tool.
    # We'll need to mock the args.
    
    # Note: create_new_hero creates files. We should use a dummy name.
    
    # Since we are inside the TestClient context, the event loop is running in background?
    # No, TestClient is sync wrapper.
    # This part is tricky with Pytest-Asyncio.
    pass

@pytest.mark.asyncio
async def test_full_flow_async():
    """
    Async test to Verify the tool execution with the initialized state.
    """
    # Manually trigger lifespan
    from super.apps.super_power_sage.super_power_sage import lifespan
    
    async with lifespan(app):
        assert state.hero_generator is not None
        
        from super.apps.super_power_sage.tools import create_new_hero
        
        # Call tool
        # This will actually create files and call Ray.
        # MUST use ainvoke for async tools!
        response = await create_new_hero.ainvoke({
            "hero_name": "IntegrationTestHero",
            "bio": "Test Bio",
            "primary_seed_name": "Heroic Strength",
            "ontology": "generated"
        })
        
        assert "Success!" in response or "Generation started" in response
        assert "IntegrationTestHero" in response

# NOTE: To run this we need pytest-asyncio and correct environment.
# But simply running this script as __main__ might be easier for the current verifying environment
# akin to verify_ray_local.py but importing the APP.

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_full_flow_async())
