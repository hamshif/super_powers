
import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "super-services", "src")))

from super.core.utils import get_app_conf, get_valid_llm, get_stage_root
from super.apps.generate_powers import generate_heroes
from super.apps.etl import ad_hoc

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("repair_hero")

def find_ontology_for_hero(stage_root: Path, hero_name: str) -> str:
    """Finds the ontology if not specified by searching profile folders."""
    safe_name = hero_name.replace(" ", "_").lower()
    profiles_root = stage_root / "hero_profiles"
    
    if not profiles_root.exists():
        return None
        
    for ontology_dir in profiles_root.iterdir():
        if ontology_dir.is_dir():
            if (ontology_dir / f"{safe_name}.json").exists():
                return ontology_dir.name
    return None

async def repair(hero_name: str, ontology: str = None, force: bool = True):
    logger.info(f"Starting repair for '{hero_name}'...")
    
    # 1. Load Config & Resources
    conf = get_app_conf(app="generate_powers")
    system_prompt = conf.get_string("generate_genome.system_prompt")
    seeds = conf.get_list("generate_powers.library.seeds")
    side_effects = conf.get_list("generate_powers.library.side_effects")
    
    seed_map = {s['name']: s for s in seeds}
    effect_map = {e['name']: e for e in side_effects}

    # 2. Setup Paths
    stage_root = get_stage_root()
    
    # Auto-detect ontology if missing
    if not ontology:
        logger.info(f"Ontology not specified. Searching for existing profile for '{hero_name}'...")
        ontology = find_ontology_for_hero(stage_root, hero_name)
        if not ontology:
            # Check local data fallback before giving up
            local_profile = Path("data/hero_profiles")
            if local_profile.exists():
                logger.info("Checking local data/hero_profiles for ontology...")
                for o_dir in local_profile.iterdir():
                     if (o_dir / f"{hero_name.replace(' ', '_').lower()}.json").exists():
                         ontology = o_dir.name
                         break
            
            if not ontology:
                logger.error(f"Could not find profile for '{hero_name}' to determine ontology. Please specify --ontology.")
                return
        logger.info(f"Resolved ontology to: '{ontology}'")

    output_dir = stage_root / "hero_genomes" / ontology
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Ensure Profile Exists in Stage
    safe_name = hero_name.replace(" ", "_").lower()
    profile_path = stage_root / "hero_profiles" / ontology / f"{safe_name}.json"
    
    if not profile_path.exists():
        logger.warning(f"Profile not found at {profile_path}. Checking local data fallback...")
        local_data_profile = Path("data/hero_profiles") / ontology / f"{safe_name}.json"
        
        if local_data_profile.exists():
             logger.info(f"Copying profile from {local_data_profile} to stage...")
             profile_path.parent.mkdir(parents=True, exist_ok=True)
             with open(local_data_profile, "r") as src, open(profile_path, "w") as dst:
                 dst.write(src.read())
        else:
             logger.error(f"Profile for '{hero_name}' not found in stage or data/hero_profiles.")
             return

    # 4. Clean Existing Genome
    # Pattern match because ID might change (e.g., SARUMA-123.json)
    # But generate_hero uses safe_name (saruman.json) in adhoc mode usually? 
    # generate_single_hero saves as {gene_id}.json OR {safe_name}.json depending on metadata logic
    # The tool said: if metadata['hero_name'] provided -> safe_filename
    
    # We will try to clean up safe_name.json
    genome_file = output_dir / f"{safe_name}.json"
    if genome_file.exists():
        if force:
            logger.info(f"Removing existing genome file: {genome_file}")
            genome_file.unlink()
        else:
            logger.info("Genome file exists. Use --force to regenerate. Checking ETL only...")
            # If we don't force regenerate, we proceed to ETL
            pass

    # 5. Generate (if needed)
    if force or not genome_file.exists():
        # Init Model
        # We assume the profile contains valid seeds. If a seed is missing from config, generate_single_hero might log warning/return.
        model = get_valid_llm(model_name="gpt-4o", temperature=0.8)
        semaphore = asyncio.Semaphore(1)
        
        logger.info(f"Generatng genome for {hero_name}...")
        try:
            await generate_heroes.generate_single_hero(
                 hero_name=hero_name,
                 ontology=ontology,
                 model=model,
                 system_prompt=system_prompt,
                 seed_map=seed_map,
                 effect_map=effect_map,
                 stage_root=stage_root,
                 output_dir=output_dir,
                 semaphore=semaphore
            )
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return

    # 6. Run ETL
    logger.info("Running Ad-Hoc ETL...")
    try:
        ad_hoc.etl_single_hero(hero_name, ontology)
        logger.info(f"Repair Complete for {hero_name}.")
    except Exception as e:
        logger.error(f"ETL Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair or Regenerate a Hero's Genome and run ETL.")
    parser.add_argument("hero_name", help="Name of the hero (e.g. 'Saruman')")
    parser.add_argument("--ontology", help="Ontology/Category (e.g. 'lotr'). Auto-detected if omitted.")
    parser.add_argument("--no-force", action="store_true", help="Skip regeneration if file exists, just run ETL.")
    
    args = parser.parse_args()
    
    force_regen = not args.no_force
    
    asyncio.run(repair(args.hero_name, args.ontology, force=force_regen))
