
"""
LangGraph agent for expanding superpowers.
"""
from __future__ import annotations

import logging
from typing import Sequence, TypedDict, Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import START, StateGraph, add_messages
from langchain_core.utils.function_calling import convert_to_openai_function

from super.apps.generate_powers.models import ExpansionResult

# Configure logger
logger = logging.getLogger(__name__)

# System Prompt based on the requirements
SYSTEM_PROMPT = """You are an expert game designer and world-builder specializing in "superpower gradients". 
Your task is to take a "Seed Ability" and expand it into a set of related abilities that share the same causal domain but vary in mechanism, constraint, scope, or cost.

For each variant ability, you must provide:
1. A creative Name.
2. A Description focused on the mechanism of action, limits, and constraints.
3. A Similarity score (0.0 to 1.0) indicating how close this variant is to the core seed concept.
4. A list of Mixed Seeds (tuples of Name and Influence) representing other concepts that blended with the seed to create this variant.

Rules:
1. Each ability must describe *mechanism + constraint*.
2. Variants should be meaningfully distinct (no synonyms).
3. Stay within the same causal domain as the seed. Do not drift into unrelated concepts.
4. Do not include game mechanics (like +1 damage), focus on narrative/physics description.
5. **No External Items**: Powers must be intrinsic to the user. Do not use cloaks, potions, gadgets, or vehicles unless they are *manifested* or *created* by the power itself (e.g., "Condensed Light Wings" is okay, "Magical Cloak" is NOT).
6. **High Fidelity**: Maintain strong conceptual adherence to the seed.
7. Generate exactly the number of variants requested (default 20).

Output must be strictly structured according to the provided schema.
"""

class AgentState(TypedDict):
    """State for the generation graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    seed: str
    n: int


class ExpansionGraphFactory:
    """Factory to create the Expansion graph."""

    @staticmethod
    def create_graph(model: BaseChatModel) -> StateGraph:
        
        # Enforce structured output using the Pydantic model
        start_model = model.with_structured_output(ExpansionResult)

        async def generate_expansion(state: AgentState):
            seed = state["seed"]
            n = state["n"]
            
            prompt = f"Expand the seed ability '{seed}' into {n} gradient variants."
            
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            # call the structured model
            try:
                result = await start_model.ainvoke(messages)
                # The result is already an instance of ExpansionResult
                return {"result": result}
            except Exception as e:
                logger.error(f"Error calling model: {e}")
                raise

        # Define a new state that includes the result
        class GraphState(AgentState):
            result: ExpansionResult

        workflow = StateGraph(GraphState)
        workflow.add_node("generate", generate_expansion)
        workflow.add_edge(START, "generate")
        
        return workflow.compile()
