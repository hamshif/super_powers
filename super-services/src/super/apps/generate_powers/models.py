
"""
Pydantic models for the Generate Powers app.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator


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


# --- Genome Generation Models ---

class PrimarySeed(BaseModel):
    seed: str = Field(..., description="Name of the seed.")
    weight: float = Field(..., description="Weight of this seed's influence (typically sum to 1.0 ± 0.2).")

class RegulatedGeneLink(BaseModel):
    gene_id: str = Field(..., description="Target Gene ID this gene regulates.")
    effect: str = Field(..., description="Regulatory effect: 'amplify', 'destabilize', 'gate', 'suppress'.")
    strength: float = Field(..., description="Strength of the regulation (0.0 to 1.0).")

class SideEffectEntry(BaseModel):
    side_effect: str = Field(..., description="Name of the side effect.")
    probability: float = Field(..., description="Probability of triggering (0.0 to 1.0).")
    severity: int = Field(..., description="Severity level (1-5).")
    trigger_condition: str = Field(..., description="Short condition string describing when this triggers.")

class MutatedGene(BaseModel):
    """A mutated gene record for the Mytho-Toon Regulatory Genome."""
    gene_id: str = Field(..., description="Unique Gene ID (e.g. TOON-019). Derived from seed name.")
    gene_role: str = Field(..., description="Role: 'anchor' (pure/stable), 'hub' (high-connectivity), 'bridge' (multi-seed mix), 'anomaly' (high-entropy/weird).")
    mutation_class: str = Field(..., description="Class: 'gain_of_function', 'loss_of_restraint', 'regulatory_instability', 'toon_causality_break', 'mythic_exception'")
    primary_seeds: List[PrimarySeed] = Field(..., min_items=1, max_items=3, description="1-3 primary seed influences.")
    secondary_seeds: List[PrimarySeed] = Field(default_factory=list, description="0-10 secondary seed influences (weight <= 0.3).")
    regulated_genes: List[RegulatedGeneLink] = Field(..., min_items=2, max_items=100, description="2-100 links to other genes.")
    side_effect_profile: List[SideEffectEntry] = Field(..., min_items=1, max_items=10, description="1-10 side effects.")
    failure_mode: str = Field(..., description="Description of how causality collapses/fails.")
    stability_index: str = Field(..., description="Index: 'stable', 'volatile', 'comedic', 'mythic_fatal'")
    confidence: float = Field(..., description="Confidence score (0.3 - 0.95).")

    @field_validator('regulated_genes')
    def deduplicate_genes(cls, v: List[RegulatedGeneLink]):
        seen = set()
        unique = []
        for link in v:
            if link.gene_id not in seen:
                seen.add(link.gene_id)
                unique.append(link)
        return unique
