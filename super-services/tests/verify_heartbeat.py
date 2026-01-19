
import asyncio
import httpx
import sys
import pytest
from super.config import get_app_conf

# Rename to internal async function
async def _run_heartbeat_live():
    # Resolve Config dynamically to match server
    # Strict adherence to Single Source of Truth (no try-except masking)
    conf = get_app_conf(app="super_power_sage")
    host = conf.get_string("super_power_sage.server.host")
    port = conf.get_int("super_power_sage.server.port")
    protocol = conf.get_string("super_power_sage.server.protocol", "http")
    
    # Construct URL using variables
    path = "super_powers_sage"
    base_url = f"{protocol}://{host}:{port}/{path}"
    print(f"Connecting to server at {base_url}...")

    # Define a custom hero to trigger creation
    prompt = "Create a hero named 'Test Heartbeat Man' who pulses with testing energy."
    
    # Increase timeout to allowing for long creation time
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream("POST", base_url, json={"prompt": prompt, "session_id": "verify_hb"}) as response:
                if response.status_code != 200:
                    print(f"FAILED: Status {response.status_code}")
                    sys.exit(1)
                
                print("Stream connected. Listening for events...")
                
                heartbeat_detected = False
                msg_count = 0
                
                async for chunk in response.aiter_lines():
                    if chunk:
                        print(f"[STREAM] {chunk}")
                        
                        if "event: tool_use" in chunk:
                            print(f"   >>> HEARTBEAT DETECTED <<<")
                            heartbeat_detected = True
                            
                        if "event: message" in chunk:
                            msg_count += 1
                
                print("\nStream finished.")
                if heartbeat_detected:
                    print("[SUCCESS] Heartbeat/Tool Use events detected!")
                else:
                    print("[FAIL] No heartbeats detected.")
                    pytest.fail("No heartbeats detected.")
                    
        except httpx.ConnectError:
            print(f"[FAIL] Could not connect to server at {host}:{port}. Is it running?")
            print(f"Run: python -m uvicorn super.apps.super_power_sage.super_power_sage:app --port {port}")
            pytest.fail("Could not connect to server.")
        except Exception as e:
            print(f"[FAIL] Error: {e}")
            pytest.fail(f"Error: {e}")

# Synchronous wrapper for pytest (since pytest-asyncio might be missing)
def test_heartbeat_live():
    asyncio.run(_run_heartbeat_live())

if __name__ == "__main__":
    try:
        # For direct execution
        asyncio.run(_run_heartbeat_live())
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
