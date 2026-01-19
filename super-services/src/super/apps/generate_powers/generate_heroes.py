"""
Script to generate full gene bundles for heroes based on their profiles.
"""
import asyncio
import logging
import os
import random
from pathlib import Path

from langchain_openai import ChatOpenAI

from super.apps.generate_powers.generate_genome import (
    generate_single_gene, 
    load_library
)
from super.apps.generate_powers.models_hero import HeroProfile
from super.core.utils import get_stage_root, get_app_conf

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # 1. Load Configs
    conf_gen = get_app_conf(app="generate_powers")
    system_prompt = conf_gen.get_string("generate_genome.system_prompt")
    concurrency = 20
    
    # 2. Load Libraries (for lookup dictionaries if needed, though profiles have the names)
    seeds = conf_gen.get_list("generate_powers.library.seeds")
    side_effects = conf_gen.get_list("generate_powers.library.side_effects")
    
    # Map names to full dicts for passing to generator (generator expects dicts with name/desc)
    seed_map = {s['name']: s for s in seeds}
    effect_map = {e['name']: e for e in side_effects}
    
    # 3. Setup Paths
    stage_root = get_stage_root()
    profile_dir = stage_root / "hero_profiles"
    output_dir_base = stage_root / "hero_genomes"
    
    if not profile_dir.exists():
        logger.error(f"Profile directory not found: {profile_dir}")
        return

    # 4. Init Model
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        raise ValueError("API Key not found!")
    
    model = ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=0.8)
    semaphore = asyncio.Semaphore(concurrency)
    
    tasks = []
    
    # 5. Iterate Profiles
    # Structure: hero_profiles/{ontology}/{hero}.json
    for ontology_dir in profile_dir.iterdir():
        if not ontology_dir.is_dir(): continue
        
        output_ontology_dir = output_dir_base / ontology_dir.name
        output_ontology_dir.mkdir(parents=True, exist_ok=True)
        
        for profile_file in ontology_dir.glob("*.json"):
            # Load Profile
            with open(profile_file, "r") as f:
                data = f.read()
                # Pydantic parsing
                try:
                    profile = HeroProfile.model_validate_json(data)
                except Exception as e:
                    logger.error(f"Failed to parse profile {profile_file}: {e}")
                    continue
            
            # Check if done
            hero_safe_name = profile.hero_name.replace(" ", "_")
            out_file = output_ontology_dir / f"{hero_safe_name}.json"
            if out_file.exists():
                logger.info(f"Skipping {profile.hero_name} (Exists)")
                continue
                
            # Prepare Generator Inputs
            # Generator expects lists of dicts for pools. 
            # We want to FORCE specific choices.
            # Trick: We pass pools containing ONLY the chosen items.
            
            # Primary Seed
            primary_seed_data = seed_map.get(profile.primary_seed_name)
            if not primary_seed_data:
                logger.warning(f"Unknown seed '{profile.primary_seed_name}' for {profile.hero_name}")
                continue
                
            # Secondary Seeds (Mixing Pool)
            mixing_pool = []
            for name in profile.secondary_seed_names:
                s = seed_map.get(name)
                if s: mixing_pool.append(s)
            
            # Side Effects Pool
            effect_pool = []
            for name in profile.side_effect_names:
                e = effect_map.get(name)
                if e: effect_pool.append(e)
                
            # Connectivity
            # 'High' -> Hub settings? 
            # Actually generate_single_gene accepts instruction string.
            if profile.estimated_connectivity == "High":
                conn_instr = "Generate 30-50 links (HUB). This is a complex, major hero."
            else:
                conn_instr = "Generate 15-25 links (Standard). Detailed but focused."
            
            # Gene ID
            # Uses Name prefix e.g. WOLVERINE-X
            # But the generator expects `gene_id`.
            # Let's clean the name: 'Spider-Man' -> 'SPIDER'
            prefix = "".join(x for x in profile.hero_name if x.isalnum()).upper()[:6]
            gene_id = f"{prefix}-{random.randint(100,999)}"
            
            # Enqueue Task
            logger.info(f"Queueing {profile.hero_name}...")
            tasks.append(
                generate_single_gene(
                    model=model,
                    system_prompt_template=system_prompt,
                    seed_name=primary_seed_data['name'],
                    seed_desc=primary_seed_data['description'],
                    gene_id=gene_id,
                    pool_seeds=mixing_pool, # Restrict mixing to profile choices
                    pool_side_effects=effect_pool, # Restrict effects to profile choices
                    semaphore=semaphore,
                    output_dir=output_ontology_dir,
                    connectivity_instruction=conn_instr,
                    metadata={"hero_name": profile.hero_name, "ontology": profile.ontology}
                )
            )
            
    # 6. execution
    logger.info(f"Processing {len(tasks)} heroes...")
    await asyncio.gather(*tasks)
    logger.info("Hero Generation Complete.")

if __name__ == "__main__":
    asyncio.run(main())
