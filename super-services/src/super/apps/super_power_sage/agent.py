"""
LangGraph agent implementation for Super Power Sage.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Sequence, TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import START, StateGraph, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

from super.apps.super_power_sage.models import UserIntent, IntentDecayRule, IntentUpdate
from super.apps.super_power_sage.tools import (
    get_hero_details, 
    search_heroes, 
    get_connected_entities, 
    find_heroes_by_ability,
    create_new_hero,
    list_ontologies
)


def update_history(current: List[str], new: List[str]) -> List[str]:
    """Appends new prompts to history, keeping only the last 3."""
    combined = current + new
    return combined[-3:]


def update_intents(current: List[UserIntent], new: List[UserIntent]) -> List[UserIntent]:
    """Replaces the intent list entirely (since we manage decay/removal manually)."""
    # For this specific logic, we might want to manually manage the list in the node
    # and return the final list. So this reducer just returns 'new' if provided.
    # Actually, simpler: define the node to return the FULL new list, so reducer is 'overwrite'.
    return new


class AgentState(TypedDict):
    """
    The state of the agent as a TypedDict.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    prompt_history: Annotated[List[str], update_history]
    intents: Annotated[List[UserIntent], update_intents]


class SageGraphFactory:
    """Factory to create the Super Power Sage graph with injected dependencies."""

    @staticmethod
    def create_graph(model: BaseChatModel, checkpointer: MemorySaver = None) -> StateGraph:
        """
        Creates and compiles the agent graph.

        Args:
            model: The language model to use.
            checkpointer: Optional persistence layer.
        
        Returns:
            A compiled LangGraph executable.
        """
        
        # --- Tools Setup ---
        tools = [get_hero_details, search_heroes, get_connected_entities, find_heroes_by_ability, create_new_hero, list_ontologies]
        model_with_tools = model.bind_tools(tools)

        # --- Node Definitions ---
        
        async def manage_context(state: AgentState):
            """
            Manages conversation history and updates user intents.
            """
            messages = state["messages"]
            current_intents = state.get("intents", [])
            history = state.get("prompt_history", [])
            
            # 1. Get current prompt
            last_message = messages[-1]
            current_prompt = last_message.content if isinstance(last_message, HumanMessage) else ""
            
            # 2. Update History (Append current)
            # The 'update_history' reducer will handle keeping top 3, we just return the new one.
            new_history_entry = [current_prompt] if current_prompt else []
            
            # 3. Intent Decay & Management
            # Only process intents if we have a new user prompt
            if not current_prompt:
                 return {}

            active_intents = []
            satisfied_ids = set() # We will simulate this check or ask LLM

            # Increment turns for existing intents
            non_decayed_intents = []
            for intent in current_intents:
                intent.turns_active += 1
                
                # Check Decay
                if intent.decay_rule == IntentDecayRule.DECAY and intent.turns_active > 3:
                   continue # Drop it
                
                non_decayed_intents.append(intent)
            
            # 4. Intent Derivation (LLM)
            # We ask the LLM: "Given history and new prompt, what are new intents? Are any old ones satisfied?"
            
            # Prepare extraction model
            extractor = model.with_structured_output(IntentUpdate)
            
            intent_system_prompt = (
                "You are an expert at understanding user intent in a creative writing session.\n"
                "Analyze the user's latest input against the context to:\n"
                "1. Identify NEW intents (goals, constraints, preferences).\n"
                "2. Check if existing 'KEEP_UNTIL_SATISFIED' intents are now satisfied/completed.\n"
                "\n"
                "Current Active Intents:\n"
                + "\n".join([f"- [{i.id}] {i.description} ({i.decay_rule})" for i in non_decayed_intents])
                + "\n\n"
                "IMPORTANT: You MUST return a JSON object with 'new_intents' and 'satisfied_intent_ids'. "
                "Use empty lists [] if there are no new intents or satisfied intents."
            )
            
            intent_messages = [
                SystemMessage(content=intent_system_prompt),
                HumanMessage(content=f"User Input: {current_prompt}")
            ]
            
            try:
                extraction: IntentUpdate = await extractor.ainvoke(intent_messages)
                
                # Process Satisfaction
                satisfied_ids.update(extraction.satisfied_intent_ids)
                
                final_intents = []
                # Add existing (if not satisfied)
                for intent in non_decayed_intents:
                    if intent.id not in satisfied_ids:
                        final_intents.append(intent)
                
                # Add new
                final_intents.extend(extraction.new_intents)
                
            except Exception as e:
                # Fallback on error: keep existing non-decayed
                # print(f"Intent extraction failed: {e}")
                final_intents = non_decayed_intents

            return {
                "prompt_history": new_history_entry,
                "intents": final_intents
            }

        async def call_model(state: AgentState):
            messages = state["messages"]
            intents = state.get("intents", [])
            history = state.get("prompt_history", [])
            
            # Construct System Prompt with Context
            context_str = "Active Context/Constraints:\n"
            if intents:
                context_str += "\n".join([f"- {i.description}" for i in intents])
            else:
                context_str += "None"
                
            history_str = "\n".join([f"- {h}" for h in history[:-1]]) # Exclude current (it's in messages)
            
            system_prompt = (
                "You are Super Power Sage, a creative assistant for generating superpowers.\n"
                "IMPORTANT: Always summarize tool outputs in natural language. DO NOT dump raw JSON or list structures to the user.\n"
                f"{context_str}\n\n"
                "CRITICAL PROTOCOL FOR MISSING HEROES:\n"
                "1. If `get_hero_details` returns 'not found':\n"
                "2. Call `search_heroes` to check for aliases (e.g. 'Strider' -> 'Aragorn').\n"
                "3. If search yields no results, YOU must CREATE the hero.\n"
                "4. First, call `list_ontologies` to see if a relevant category exists (e.g. 'looney_tunes').\n"
                "   - If the hero fits a new category (e.g. 'Gandalf' -> 'lotr'), use it.\n"
                "   - Otherwise use 'generated'.\n"
                "5. INFORM the user: 'I couldn't find [Name], but I am generating them now... (This may take a moment)'.\n"
                "6. Call `create_new_hero(name, ..., ontology=...)`.\n"
                f"Recent User Prompts:\n{history_str}\n"
            )
            
            # Prepend System message
            # Filter out old system messages to avoid duplication if we loop
            filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
            final_messages = [SystemMessage(content=system_prompt)] + filtered_messages
            
            response = await model_with_tools.ainvoke(final_messages)
            return {"messages": [response]}

        # --- Graph Construction ---
        
        workflow = StateGraph(AgentState)
        workflow.add_node("manage_context", manage_context)
        workflow.add_node("model", call_model)
        workflow.add_node("tools", ToolNode(tools))
        
        workflow.add_edge(START, "manage_context")
        workflow.add_edge("manage_context", "model")
        
        # ReAct conditional routing
        workflow.add_conditional_edges(
            "model",
            tools_condition,
        )
        workflow.add_edge("tools", "model")
        
        return workflow.compile(checkpointer=checkpointer)
