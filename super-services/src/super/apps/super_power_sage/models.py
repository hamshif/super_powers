from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class IntentDecayRule(str, Enum):
    """
    Rules determining how long a UserIntent persists in the session.
    """
    PERSIST_ALWAYS = "PERSIST_ALWAYS"
    PERSIST_ALL_SESSION = "PERSIST_ALL_SESSION"
    DECAY = "DECAY"
    KEEP_UNTIL_SATISFIED = "KEEP_UNTIL_SATISFIED"

class UserIntent(BaseModel):
    """
    Represents a derived user intent/goal.
    """
    id: str = Field(description="Unique identifier for this intent instance.")
    description: str = Field(description="Clear description of the user's intent or constraint (e.g., 'User wants a villain', 'Must be blue').")
    decay_rule: IntentDecayRule = Field(description="Lifecycle rule for this intent.")
    turns_active: int = Field(default=0, description="How many turns this intent has been active.")
    satisfied: bool = Field(default=False, description="Whether the intent has been satisfied.")

class IntentUpdate(BaseModel):
    """
    Structured output for the intent derivation step.
    """
    new_intents: List[UserIntent] = Field(description="List of NEW intents derived from the latest user message.")
    satisfied_intent_ids: List[str] = Field(description="List of IDs of EXISTING intents that are satisfied by the assistant's previous actions or the user's current confirmation.")


class SseEventType(str, Enum):
    """
    Types of events sent via SSE.
    """
    STREAM_OF_THOUGHT = "stream_of_thought"
    HEARTBEAT = "heartbeat"
    ANSWER = "answer"
    HERO_DATA = "hero_data"

class SseEvent(BaseModel):
    """
    A unified model for Server-Sent Events.
    """
    event: SseEventType
    data: str
