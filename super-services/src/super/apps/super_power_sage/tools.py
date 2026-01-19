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
    global _warehouse_root
    if _warehouse_root:
        return _warehouse_root
    
    # Try Env
    env_root = os.getenv("WAREHOUSE_ROOT")
    if env_root and os.path.exists(env_root):
        _warehouse_root = env_root
        return env_root

    # Use System Standard Stage Root
    try:
        from super.core.utils import get_stage_root
        stage_root = get_stage_root()
        warehouse_path = stage_root / "warehouse"
        if warehouse_path.exists():
             _warehouse_root = str(warehouse_path)
             return _warehouse_root
    except ImportError:
        pass

    # Try relative from current working directory (assuming we are in project root or subfolder)
    # Common cases:
    # 1. /home/gideon/tmp/super_powers/super-services -> ../data/warehouse
    # 2. /home/gideon/tmp/super_powers -> data/warehouse
    
    cwd = os.getcwd()
    candidates = [
        os.path.join(cwd, "../data/warehouse"),
        os.path.join(cwd, "data/warehouse"),
        os.path.join(cwd, "../../data/warehouse"), # original default
        "/home/gideon/tmp/super_powers/data/warehouse" # Absolute fallback
    ]
    
    for path in candidates:
        if os.path.exists(path):
            _warehouse_root = os.path.abspath(path)
            return _warehouse_root
            
    # Default fallback
    return os.path.abspath(os.path.join(cwd, "../../data/warehouse"))

def _get_gm() -> GraphManager:
    global _gm
    if _gm is None:
        root = _get_warehouse_root()
        _gm = GraphManager(warehouse_root=root)
    return _gm

@tool
def get_hero_details(hero_name: str, ontology: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve detailed information about a hero, including their bio, genetics, and gene regulation network.
    
    Args:
        hero_name: The exact name of the hero (e.g., "Bugs Bunny").
        ontology: Optional ontology to optimize search (e.g., "looney_tunes").
    """
    root = _get_warehouse_root()
    data = get_hero_data(hero_name, ontology=ontology, warehouse_root=root)
    if data:
        return data
    return {"error": f"Hero '{hero_name}' not found."}

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
def get_connected_entities(entity_name: str, depth: int = 1) -> Dict[str, Any]:
    """
    Explore the knowledge graph to find entities (Heroes, Genes, powers) connected to a given entity.
    Useful for answering "Who does X know?" or "What is related to gene Y?".
    
    Args:
        entity_name: Name of the node to start traversal from.
        depth: How many hops to traverse (default 1, max 2 recommended).
    """
    gm = _get_gm()
    
    # Check if node exists
    if entity_name not in gm.G:
        return {"error": f"Entity '{entity_name}' not found in the graph."}
        
    sub_G = gm.subgraph_for_hero(entity_name, depth=depth)
    if not sub_G:
        return {"error": "Could not extract subgraph."}
        
    # Convert subgraph to a simple JSON structure
    nodes = []
    for n, data in sub_G.nodes(data=True):
        nodes.append({"id": n, "type": data.get('type', 'Unknown'), "label": data.get('label', n)})
        
    edges = []
    for u, v, data in sub_G.edges(data=True):
        edges.append({"source": u, "target": v, "relation": data.get('relation', 'RELATED')})
        
    return {
        "center": entity_name,
        "nodes": nodes,
        "edges": edges
    }

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
        genome_dir = stage_root / "hero_genomes" / ontology
        genome_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Save Profile
        profile_path = profile_dir / f"{safe_name}.json"
        with open(profile_path, "w") as f:
            f.write(profile.model_dump_json(indent=2))
            
        print(f"Created profile for {hero_name} at {profile_path}")
        
        # 3. Generate Genome (Invoke generate_heroes logic)
        # Load config (cached) to avoid blocking I/O
        global _cached_conf_gen
        if _cached_conf_gen is None:
            # First time load might block slightly, but subsequent calls won't.
            # Ideally we'd run this in executor too, but it's acceptable for first run.
            _cached_conf_gen = get_app_conf(app="generate_powers")
            
        conf_gen = _cached_conf_gen
        seeds = conf_gen.get_list("generate_powers.library.seeds")
        effects = conf_gen.get_list("generate_powers.library.side_effects")
        seed_map = {s['name']: s for s in seeds}
        effect_map = {e['name']: e for e in effects}
        
        system_prompt = conf_gen.get_string("generate_genome.system_prompt")
        
        # Init Model (Robust)
        # Init Model (Robust)
        from super.core import utils
        model = await utils.get_valid_llm_async(model_name="gpt-4o", temperature=0.8)
        semaphore = asyncio.Semaphore(1) # Single task
        
        # Run Generation
        await generate_heroes.process_hero(
            profile=profile,
            model=model,
            system_prompt=system_prompt,
            seed_map=seed_map,
            effect_map=effect_map,
            semaphore=semaphore,
            output_dir=genome_dir
        )
            
        # 4. ETL (Ad-Hoc Pandas)
        # Using lightweight Pandas ETL for single hero to avoid Spark overhead.
        # Run in default ThreadPool executor (None) to avoid ProcessPool startup cost (which blocks).
        # Pandas/PyArrow releases GIL for I/O, so threads are fine here.
        # ad_hoc is imported at top level now.
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, ad_hoc.etl_single_hero, hero_name, ontology)
        
        # 5. Verification
        # Check if genes are retrievable
        verify_data = get_hero_data(hero_name, ontology, warehouse_root=stage_root / "warehouse")
        if not verify_data or not verify_data.get('master_gene'):
             return f"Success! Hero {hero_name} created, but **WARNING**: Gene data could not be verified in warehouse immediately. Please check logs."
        
        return f"Success! Hero {hero_name} has been created, generated, and added to the warehouse."
        
    except Exception as e:
        import traceback
        return f"Failed to create hero: {e} \n{traceback.format_exc()}"

    finally:
        # Cache Invalidation
        # Force GraphManager to reload on next call (intake fresh Parquet)
        global _gm
        _gm = None
        print("DEBUG: GraphManager cache cleared.")
