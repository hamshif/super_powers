"""
Tool definitions for Super Power Sage.
These tools expose core domain logic to the LLM.
"""
import os
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

from super.core.warehouse import get_hero_data, get_all_heroes_data
from super.core.graph import GraphManager

# Global GraphManager instance to avoid reloading on every call
_gm = None
_warehouse_root = None

def _get_warehouse_root() -> str:
    global _warehouse_root
    if _warehouse_root:
        return _warehouse_root
    
    # Try Env
    env_root = os.getenv("WAREHOUSE_ROOT")
    if env_root and os.path.exists(env_root):
        _warehouse_root = env_root
        return env_root

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
        
        # Filter by score threshold (e.g., > 70)
        # fuzzy_matches is list of (name, score)
        matched_names = [name for name, score in fuzzy_matches if score > 70]
        
        if matched_names:
             # Filter dataframe by these names
             return df[df['hero_name'].isin(matched_names)].to_dict(orient='records')
             
    except ImportError:
        pass
        
    return []

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
def find_heroes_by_ability(ability_keyword: str) -> List[str]:
    """
    Find heroes who have a specific ability or keyword in their bio (e.g., "fly", "strength").
    
    Args:
        ability_keyword: The keyword to search for (e.g., "fly").
    """
    gm = _get_gm()
    
    heroes = []
    keyword = ability_keyword.lower()
    
    for n, data in gm.G.nodes(data=True):
        if data.get('type') == 'Hero':
            bio = data.get('bio', '').lower()
            if keyword in bio:
                heroes.append(n)
                
    return heroes
