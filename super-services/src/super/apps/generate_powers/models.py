
"""
Pydantic models for the Generate Powers app.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class AbilityDescriptor(BaseModel):
    """Describes a single ability."""
    description: str = Field(..., description="A concise, mechanism-focused description of the ability.")


class MixedSeed(BaseModel):
    """Represents a contribution from another concept or seed."""
    name: str = Field(..., description="The name of the mixed concept or seed.")
    influence: float = Field(..., ge=0.0, le=1.0, description="The degree of influence this mixed concept has (0.0 to 1.0).")


class GradientVariant(BaseModel):
    """A single gradient variant ability."""
    name: str = Field(..., description="Name of the variant ability")
    description: str = Field(..., description="Mechanism-focused description")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Degree of similarity to the initial seed concept (0.0 to 1.0).")
    mixed_seeds: List[MixedSeed] = Field(..., description="List of other concepts or seeds that influenced this variant.")
    side_effects: List[str] = Field(default_factory=list, description="List of side effects or flaws applied to this variant.")


class ExpansionResult(BaseModel):
    """The structured result of an ability expansion."""
    seed_name: str = Field(..., description="The name of the seed ability.")
    seed_description: str = Field(..., description="Description of the seed ability.")
    gradient: List[GradientVariant] = Field(..., description="List of 20 gradient-related abilities.")
