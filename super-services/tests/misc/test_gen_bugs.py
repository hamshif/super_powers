"""
Script to generate ONLY Bugs Bunny genome for verification.
"""
import asyncio
import logging
import os
import random
from pathlib import Path

from langchain_openai import ChatOpenAI

from super.apps.generate_powers.generate_genome import (
    generate_single_gene
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
    
    # 2. Get Bugs Profile
    stage_root = get_stage_root()
    profile_path = stage_root / "hero_profiles/looney_tunes/Bugs Bunny.json"
    
    if not profile_path.exists():
        logger.error("Bugs Bunny profile not found!")
        return
        
    with open(profile_path, "r") as f:
        profile = HeroProfile.model_validate_json(f.read())
        
    logger.info(f"Loaded Profile: {profile.hero_name}")
    
    # 3. Load Libraries (Quick Load)
    seeds = conf_gen.get_list("generate_powers.library.seeds")
    side_effects = conf_gen.get_list("generate_powers.library.side_effects")
    
    seed_map = {s['name']: s for s in seeds}
    effect_map = {e['name']: e for e in side_effects}
    
    # 4. Prepare Generator Inputs
    # Primary Seed
    primary_seed_data = seed_map.get(profile.primary_seed_name)
    if not primary_seed_data:
        raise ValueError("Primary seed not found in library")
        
    # Pool filters
    mixing_pool = [s for s in seeds if s['name'] in profile.secondary_seed_names]
    effect_pool = [e for e in side_effects if e['name'] in profile.side_effect_names]
    
    # 5. Output
    output_dir = stage_root / "hero_genomes/looney_tunes"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean old files to ensure we see the new one
    # We want to confirm bugs_bunny.json creation
    target_file = output_dir / "bugs_bunny.json"
    if target_file.exists():
        target_file.unlink()
        logger.info("Deleted existing bugs_bunny.json")
    
    # 6. Run Limit 1
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    model = ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=0.4)
    semaphore = asyncio.Semaphore(1)
    
    conn_instr = "Generate 30-50 links (HUB)."
    gene_id = "BUGS-TEST-001" # Temporary ID, filename should be bugs_bunny.json regardless
    
    logger.info("Generating Bugs Bunny Genome...")
    await generate_single_gene(
        model=model,
        system_prompt_template=system_prompt,
        seed_name=primary_seed_data['name'],
        seed_desc=primary_seed_data['description'],
        gene_id=gene_id,
        pool_seeds=mixing_pool,
        pool_side_effects=effect_pool,
        semaphore=semaphore,
        output_dir=output_dir,
        connectivity_instruction=conn_instr,
        metadata={"hero_name": profile.hero_name, "ontology": profile.ontology}
    )
    
    if target_file.exists():
        logger.info(f"SUCCESS: {target_file} created.")
    else:
        logger.error("FAILURE: bugs_bunny.json not found.")

if __name__ == "__main__":
    asyncio.run(main())
