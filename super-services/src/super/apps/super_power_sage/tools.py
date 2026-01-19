"""
Tool definitions for Super Power Sage.
These tools expose core domain logic to the LLM.
"""
import os
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

from super.core.warehouse import get_hero_data, get_all_heroes_data
from super.core.graph import GraphManager
from super.core.utils import get_stage_root, get_app_conf
from super.apps.generate_powers.models_hero import HeroProfile
from super.apps.generate_powers import generate_heroes
from super.apps.etl import flatten_heroes
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import asyncio
from pathlib import Path
from super.apps.etl import ad_hoc  # Import at top-level to avoid runtime blocking

# Global GraphManager instance to avoid reloading on every call
_gm = None
_warehouse_root = None
_cached_conf_gen = None  # Cache for generate_powers config

def _get_warehouse_root() -> str:
    """Resolve warehouse root using central configuration."""
    global _warehouse_root
    if _warehouse_root:
        return _warehouse_root
    
    stage_root = get_stage_root()
    warehouse_path = stage_root / "warehouse"
    
    _warehouse_root = str(warehouse_path.resolve())
    return _warehouse_root

def _get_gm() -> GraphManager:
    global _gm
    if _gm is None:
        root = _get_warehouse_root()
        _gm = GraphManager(warehouse_root=root)
    return _gm

@tool
async def get_hero_details(hero_name: str) -> str:
    """
    Retrieves detailed information about a hero, including their genome.
    
    Args:
        hero_name: The name of the hero to retrieve.
        
    Returns:
        A concise summary of the hero. Detailed genetic data is sent to the user's view directly.
    """
    root = _get_warehouse_root()
    data_str = get_hero_data(hero_name, warehouse_root=root)
    if not data_str:
        return f"Hero '{hero_name}' not found in the database. Try searching for aliases."
    
    
    
    # Check if data_str is already a dict (pandas return) or string
    if isinstance(data_str, dict):
        data = data_str
    else:
        # Parse the data to send structured JSON to SSE
        import json
        try:
            data = json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
             # Fallback if decode fails or if data_str is not string/bytes
             data = {"raw": str(data_str)} 
    
    # Push to side-channel
    from super.apps.super_power_sage import state
    state.data_queue.append({
        "type": "genetic_data",
        "hero": hero_name,
        "payload": data
    })
    
    # Return Summary to LLM
    bio = data.get("profile", {}).get("bio", "No bio available.")[:200]
    return (
        f"Genetic data for '{hero_name}' has been retrieved and sent to the user's view.\n"
        f"Brief Bio: {bio}...\n"
        f"(Full details are visible to the user)"
    )

@tool
def search_heroes(query: str) -> List[Dict[str, Any]]:
    """
    Search for heroes by name or partial name. Use this when you don't know the exact hero name.
    
    Args:
        query: The search string (e.g., "villain", "rabbit", "super").
    """
    root = _get_warehouse_root()
    df = get_all_heroes_data(warehouse_root=root)
    if df.empty:
        return []
    
    
    # Simple contain check first (fast)
    mask = (
        df['hero_name'].str.contains(query, case=False, na=False) | 
        df['bio'].str.contains(query, case=False, na=False)
    )
    result = df[mask]
    
    # If standard search returns results, return them
    if not result.empty:
         return result.head(10).to_dict(orient='records')
         
    # Fallback to Fuzzy Search
    try:
        from thefuzz import process, fuzz
        
        # We search against hero names
        # process.extract returns list of (match, score) when input is a list
        names = df['hero_name'].tolist()
        fuzzy_matches = process.extract(query, names, limit=10, scorer=fuzz.partial_ratio)
        
        # Filter by score threshold (e.g., > 90) to avoid noise (like Olórin vs Robin)
        # fuzzy_matches is list of (name, score)
        matched_names = [name for name, score in fuzzy_matches if score > 90]
        
        if matched_names:
             # Filter dataframe by these names
             return df[df['hero_name'].isin(matched_names)].to_dict(orient='records')
             
    except ImportError:
        pass
        
    # Fallback to Smart Search (LLM Alias Expansion)
    # Only if we found nothing so far
    try:
        if len(query.split()) > 0: # Avoid empty semantic search
            print(f"DEBUG: Smart searching for '{query}'...")
            
            # API Key Fallback with active check
            from super.core import utils
            llm = utils.get_valid_llm(model_name="gpt-4o", temperature=0)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a superhero expert. Given a search query, list up to 3 alternative names, aliases, or real names for the character. Return ONLY a comma-separated list of names. If unknown, return nothing."),
                ("human", "{query}")
            ])
            
            chain = prompt | llm
            response = chain.invoke({"query": query})
            aliases = [a.strip() for a in response.content.split(",") if a.strip()]
            
            print(f"DEBUG: LLM suggested aliases: {aliases}")
            
            if aliases:
                # Search for each alias
                # We reuse the dataframe logic
                # We can construct a combined regex mask
                # escape regex chars just in case
                import re
                combined_query = "|".join([re.escape(a) for a in aliases])
                mask = (
                    df['hero_name'].str.contains(combined_query, case=False, na=False) | 
                    df['bio'].str.contains(combined_query, case=False, na=False)
                )
                smart_result = df[mask]
                if not smart_result.empty:
                    return smart_result.head(10).to_dict(orient='records')

    except Exception as e:
        print(f"Smart search failed: {e}")
        pass

    return []

@tool
def list_ontologies() -> List[str]:
    """
    List all available ontologies (universes/categories) in the Super Power Warehouse.
    Useful for checking if a category like 'lotr' or 'star_wars' already exists.
    """
    try:
        root = _get_warehouse_root()
        df = get_all_heroes_data(warehouse_root=root)
        if df.empty:
            return []
        
        # Extract unique ontologies
        # Normalized to lowercase for consistency
        ontologies = sorted(df['ontology'].dropna().unique().tolist())
        return ontologies
    except Exception as e:
        return [f"Error listing ontologies: {e}"]

@tool
async def get_connected_entities(entity_name: str, degree: int = 1) -> str:
    """
    Finds entities connected to the given entity in the knowledge graph.
    Useful for finding side effects, seeds, or other heroes related to a specific trait.
    
    Args:
        entity_name: The central entity to search for (e.g., 'Batman', 'Super Strength').
        degree: The number of hops to traverse (default: 1).
        
    Returns:
        A summary of connections. Visual graph data is sent to the user's view directly.
    """
    manager = _get_gm() # Use global manager
    graph_data = manager.get_subgraph_for_node(entity_name, degree)
    
    # Push to side-channel
    from super.apps.super_power_sage import state
    state.data_queue.append({
        "type": "graph_view",
        "center": entity_name,
        "payload": graph_data
    })
    
    # Generate Summary for LLM
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    node_count = len(nodes)
    edge_count = len(edges)
    
    # Create text summary of immediate connections
    summary_lines = [f"Found {node_count} nodes and {edge_count} edges connected to '{entity_name}'."]
    
    if edges:
        examples = edges[:5]
        summary_lines.append("Examples:")
        for e in examples:
            summary_lines.append(f"- {e['source']} {e['relation']} {e['target']}")
    
    return "\n".join(summary_lines)

@tool
def find_heroes_by_ability(ability: str) -> List[Dict[str, Any]]:
    """
    Find heroes who possess a specific ability or power.
    
    Args:
        ability: The ability or power to search for (e.g., "flight", "regeneration").
    """
    # For now, we reuse the robust search logic which covers bio and name, 
    # and effectively searches for abilities mentioned in the bio.
    # In a more advanced version, this would search the 'hero_genes' table specifically.
    
    # Let's search hero_genes first if possible, or just default to semantic search on profiles
    # since bio usually contains the powers.
    return search_heroes.invoke({"query": ability})

@tool
async def create_new_hero(
    hero_name: str, 
    bio: str, 
    primary_seed_name: str = "Heroic Strength", 
    side_effects: List[str] = [], 
    estimated_connectivity: str = "Low",
    ontology: str = "generated"
) -> str:
    """
    Creates a new hero from scratch! This will generate their DNA, Powers, and add them to the warehouse.
    
    Args:
        hero_name: The name of the new hero.
        bio: A short description of the hero.
        primary_seed_name: The main power source/seed (e.g., "Super Strength", "Flight", "Speed", "Magic", "Telepathy").
        side_effects: List of potential side effects (e.g., "Hubris", "Mutation").
        estimated_connectivity: Complexity of the hero ("Low" or "High").
        ontology: The universe or category (e.g., "generated", "lotr", "star_wars"). Defaults to "generated".
    """
    try:
        # 1. Setup Context
        stage_root = get_stage_root()
        ontology = ontology.lower().replace(" ", "_") # Normalize
        safe_name = hero_name.replace(" ", "_").replace("'", "").lower()
        
        # Ensure directories
        profile_dir = stage_root / "hero_profiles" / ontology
        profile_dir.mkdir(parents=True, exist_ok=True)
        # Genome dir creation is handled by actor, but safe to do here too
        
        # 2. Create Profile
        profile = HeroProfile(
            hero_name=hero_name,
            ontology=ontology,
            primary_seed_name=primary_seed_name,
            secondary_seed_names=[], # Simplifying for tool interaction
            side_effect_names=side_effects,
            bio=bio,
            estimated_connectivity=estimated_connectivity
        )
        
        # Save Profile (Needed by Actor)
        profile_path = profile_dir / f"{safe_name}.json"
        with open(profile_path, "w") as f:
            f.write(profile.model_dump_json(indent=2))
            
        print(f"Created profile for {hero_name} at {profile_path}")
        
        # 3. Submit to Ray Actor
        # Retrieve the global actor instance from the shared state module
        from super.apps.super_power_sage import state
        
        if state.hero_generator is None:
             return "Error: Hero Generation Service (Ray Actor) is not initialized. Cannot create hero."
        
        # Submit task
        print(f"Submitting generation task for {hero_name} to Ray Actor...")
        result = await state.hero_generator.generate_hero.remote(hero_name, ontology)
        
        # 4. ETL (Ad-Hoc)
        # The Actor only generates the JSON. We still need to ETL it to the warehouse.
        # Note: Eventual consistency race condition is handled by ad_hoc.py's retry loop now!
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, ad_hoc.etl_single_hero, hero_name, ontology)
        
        # 5. Verification
        verify_data = get_hero_data(hero_name, ontology, warehouse_root=stage_root / "warehouse")
        if not verify_data or not verify_data.get('master_gene'):
             return f"Success! Hero {hero_name} created, but **WARNING**: Gene data could not be verified in warehouse immediately. Please check logs. Raw Result: {result}"
        
        return f"Success! Hero {hero_name} has been created. {result}"
        
    except Exception as e:
        import traceback
        return f"Failed to create hero: {e} \n{traceback.format_exc()}"

    finally:
        # Cache Invalidation
        global _gm
        _gm = None
        print("DEBUG: GraphManager cache cleared.")
