import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from super.apps.super_power_sage.agent import SageGraphFactory
from super.apps.super_power_sage.models import UserIntent, IntentDecayRule, IntentUpdate


def test_intent_retention_and_decay():
    """
    Verifies that:
    1. Intents are created and persisted across turns.
    2. Turn counters increment.
    3. DECAY rules remove intents after threshold.
    """
    asyncio.run(_async_test_logic())


async def _async_test_logic():
    
    # --- SETUP MOCKS ---
    # content generation model
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock()
    
    # extractor (structured output)
    mock_extractor = AsyncMock()
    
    # with_structured_output is called synchronously to get the extractor
    mock_model.with_structured_output.return_value = mock_extractor
    
    # --- SCENARIO DATA ---
    
    # Intent A: Persist Always (e.g. "Create Villain")
    intent_a = UserIntent(
        id="intent_A", 
        description="Create Villain", 
        decay_rule=IntentDecayRule.PERSIST_ALWAYS
    )
    
    # Intent B: Decay (e.g. "Make him blue")
    intent_b = UserIntent(
        id="intent_B", 
        description="Blue Skin", 
        decay_rule=IntentDecayRule.DECAY
    )

    # Turn 1 Output: Create Intent A
    update_1 = IntentUpdate(new_intents=[intent_a], satisfied_intent_ids=[])
    
    # Turn 2 Output: Create Intent B
    update_2 = IntentUpdate(new_intents=[intent_b], satisfied_intent_ids=[])
    
    # Turn 3, 4, 5, 6 Output: No new intents, just filler conversation
    update_empty = IntentUpdate(new_intents=[], satisfied_intent_ids=[])
    
    # Mock sequence for extractor (Turn 1, Turn 2, Turn 3, Turn 4, Turn 5, Turn 6)
    mock_extractor.ainvoke.side_effect = [
        update_1, 
        update_2, 
        update_empty, 
        update_empty, 
        update_empty, 
        update_empty
    ]
    
    # Mock chat response
    mock_model.ainvoke.return_value = AIMessage(content="Acknowledged.")

    # --- EXECUTION ---
    
    checkpointer = MemorySaver()
    graph = SageGraphFactory.create_graph(mock_model, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test_session_retention"}}
    
    # TURN 1: User sets Intent A
    await graph.ainvoke({"messages": [HumanMessage(content="Create a villain.")]}, config=config)
    
    state = await graph.aget_state(config)
    intents = state.values["intents"]
    assert len(intents) == 1
    assert intents[0].id == "intent_A"
    assert intents[0].turns_active == 0
    
    # TURN 2: User sets Intent B
    await graph.ainvoke({"messages": [HumanMessage(content="Make him blue.")]}, config=config)
    
    state = await graph.aget_state(config)
    intents = {i.id: i for i in state.values["intents"]}
    assert len(intents) == 2
    assert intents["intent_A"].turns_active == 1 # Incremented at start of Turn 2
    assert intents["intent_B"].turns_active == 0 # Newly created in Turn 2
    
    # TURN 3: Filler (A=2, B=1)
    await graph.ainvoke({"messages": [HumanMessage(content="Filler 1")]}, config=config)
    state = await graph.aget_state(config)
    intents = {i.id: i for i in state.values["intents"]}
    assert intents["intent_B"].turns_active == 1 
    
    # TURN 4: Filler (A=3, B=2)
    await graph.ainvoke({"messages": [HumanMessage(content="Filler 2")]}, config=config)
    state = await graph.aget_state(config)
    intents = {i.id: i for i in state.values["intents"]}
    assert intents["intent_B"].turns_active == 2 
    
    # TURN 5: Filler (A=4, B=3)
    # Intent B is DECAY. Threshold > 3? 
    # Logic: if intent.decay_rule == IntentDecayRule.DECAY and intent.turns_active > 3: continue
    # At start of Turn 5, B was 2. Increments to 3. 3 > 3 is False. Keeps it.
    await graph.ainvoke({"messages": [HumanMessage(content="Filler 3")]}, config=config)
    state = await graph.aget_state(config)
    intents = {i.id: i for i in state.values["intents"]}
    assert "intent_B" in intents
    assert intents["intent_B"].turns_active == 3
    
    # TURN 6: Filler (A=5, B=4)
    # At start of Turn 6, B is 3. Increments to 4. 4 > 3 is True. DROPS IT.
    await graph.ainvoke({"messages": [HumanMessage(content="Filler 4")]}, config=config)
    state = await graph.aget_state(config)
    intents = {i.id: i for i in state.values["intents"]}
    
    # VERIFICATION
    assert "intent_A" in intents, "Intent A (Persist Always) should be retained."
    assert "intent_B" not in intents, "Intent B (Decay) should be dropped after >3 turns."
    assert intents["intent_A"].turns_active == 5
