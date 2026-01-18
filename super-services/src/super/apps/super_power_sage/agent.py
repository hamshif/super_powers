
"""
LangGraph agent implementation for Super Power Sage.
"""
from __future__ import annotations

from typing import Annotated, Sequence, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import START, StateGraph, add_messages
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    """
    The state of the agent as a TypedDict.
    LangGraph recommends TypedDict for state, but we can use Pydantic for validation inside nodes.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]


class SageGraphFactory:
    """Factory to create the Super Power Sage graph with injected dependencies."""

    @staticmethod
    def create_graph(model: BaseChatModel) -> StateGraph:
        """
        Creates and compiles the agent graph.

        Args:
            model: The language model to use (e.g., ChatOpenAI).
        
        Returns:
            A compiled LangGraph executable.
        """
        
        # --- Node Definitions ---
        
        async def call_model(state: AgentState):
            messages = state["messages"]
            response = await model.ainvoke(messages)
            return {"messages": [response]}

        # --- Graph Construction ---
        
        workflow = StateGraph(AgentState)
        workflow.add_node("model", call_model)
        workflow.add_edge(START, "model")
        
        return workflow.compile()
