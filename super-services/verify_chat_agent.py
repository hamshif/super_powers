import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from super.apps.super_power_sage.agent import SageGraphFactory

# Setup
api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
if not api_key:
    # Try looking in .env if not in real env (simple check)
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("OMGENE_OPEN_AI_API_KEY="):
                    api_key = line.strip().split("=", 1)[1]
                    os.environ["OMGENE_OPEN_AI_API_KEY"] = api_key
                    break

if not api_key:
    print("SKIPPING: OMGENE_OPEN_AI_API_KEY not found.")
    exit(0)

async def main():
    print("Initializing Agent Graph...")
    model = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    checkpointer = MemorySaver()
    graph = SageGraphFactory.create_graph(model, checkpointer=checkpointer)
    
    print("Graph Compiled.")
    
    # Test Prompt that should trigger a tool
    prompt = "Find verify details for Batman."
    # We expect 'get_hero_details' or similar.
    
    inputs = {"messages": [HumanMessage(content=prompt)]}
    config = {"configurable": {"thread_id": "test_session"}}
    
    print(f"Sending prompt: '{prompt}'")
    
    print("\n--- Streaming Responses ---")
    async for event in graph.astream(inputs, config=config, stream_mode="updates"):
        for node, output in event.items():
            print(f"\n[Node: {node}]")
            if "messages" in output:
                last_msg = output["messages"][-1]
                # Check for tool calls
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    print(f"  Tool Calls: {last_msg.tool_calls}")
                # Check for content
                if last_msg.content:
                    print(f"  Content: {last_msg.content[:100]}...") # Truncate
    
    print("\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(main())
