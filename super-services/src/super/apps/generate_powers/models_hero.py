from typing import List, Optional
from pydantic import BaseModel, Field

class HeroProfile(BaseModel):
    """
    Profile of a Hero's powers mapped to our specific game ontology.
    """
    hero_name: str = Field(description="Name of the hero (e.g., 'Wolverine').")
    ontology: str = Field(description="Source ontology (e.g., 'X-Men', 'Marvel').")
    
    # Gene Selection
    primary_seed_name: str = Field(description="The single most dominant Power Seed from the library that defines this hero.")
    secondary_seed_names: List[str] = Field(description="List of 1-3 additional Power Seeds that contribute to their abilities.")
    
    # Side Effects
    side_effect_names: List[str] = Field(description="List of canonical Side Effects that fit this hero's drawbacks or nature.")
    
    # Flavour
    bio: str = Field(description="A 1-sentence bio describing their power set in the context of the game.")
    
    # Complexity Estimation
    estimated_connectivity: str = Field(description="Does this hero have complex, multi-faceted powers? ('High', 'Medium', 'Low').")
