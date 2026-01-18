
"""
Pydantic models for the Generate Powers app.
"""
from __future__ import annotations

from typing import Dict, List
from pydantic import BaseModel, Field


class AbilityDescriptor(BaseModel):
    """Describes a single ability."""
    description: str = Field(..., description="A concise, mechanism-focused description of the ability.")


class GradientVariant(BaseModel):
    """A single gradient variant ability."""
    name: str = Field(..., description="Name of the variant ability")
    description: str = Field(..., description="Mechanism-focused description")


class ExpansionResult(BaseModel):
    """The structured result of an ability expansion."""
    seed_name: str = Field(..., description="The name of the seed ability.")
    seed_description: str = Field(..., description="Description of the seed ability.")
    gradient: List[GradientVariant] = Field(..., description="List of 20 gradient-related abilities.")
