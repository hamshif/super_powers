
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

class AgentState(TypedDict):
    """State for the generation graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    seed: str
    n: int


class ExpansionGraphFactory:
    """Factory to create the Expansion graph."""

    @staticmethod
    def create_graph(model: BaseChatModel, system_prompt: str) -> StateGraph:
        
        # Enforce structured output using the Pydantic model
        start_model = model.with_structured_output(ExpansionResult)

        async def generate_expansion(state: AgentState):
            seed = state["seed"]
            n = state["n"]
            
            prompt = f"Expand the seed ability '{seed}' into {n} gradient variants."
            
            messages = [
                SystemMessage(content=system_prompt),
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
