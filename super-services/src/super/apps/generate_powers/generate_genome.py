import random
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in path (Standard Pattern)
# We assume the script is run from project root or 'super-services' is importable.
# Using relative path injection if needed, similar to generate_powers.py refactor expectations 
# but per instructions we should rely on installed package or PYTHONPATH. 
# For safety in this environment:
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from super.core.utils import get_app_conf
from super.apps.generate_powers.models import MutatedGene
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)

# --- Configuration & Setup ---

from pyhocon import ConfigFactory

def load_library(path: Path) -> List[Dict]:
    """Loads a library file (JSON or HOCON)."""
    if not path.exists():
         raise FileNotFoundError(f"Library file not found: {path}")
    
    if path.suffix == ".conf":
        # Parse HOCON and assume structure is just a list? 
        # Actually HOCON root must be object. The file likely has a root key.
        # Let's inspect the seed file next. For now, assume it returns list-like config or we extract.
        # Based on app.conf `include`, these files probably define keys.
        # We need to read the config and extract the relevant key?
        # WAIT: app.conf includes them. They are merged into root config.
        # So we shouldn't "load" them as separate files if they are just HOCON fragments.
        # BUT if I want to "load_library" I should probably treat them as data.
        # Let's see what the user did before.
        # Ah, in turn 2257 generate_genome.py used `conf.get_list("generate_powers.library.seeds")`.
        # This implies standard ConfigFactory loading merges them.
        # So `profile_hero.py` should ALSO access them via `conf_gen.get_list(...)` instead of manually loading files!
        pass 
        
    with open(path, "r") as f:
         return json.load(f)

async def generate_single_gene(
    model: ChatOpenAI,
    system_prompt_template: str,
    seed_name: str,
    seed_desc: str,
    gene_id: str,
    pool_seeds: List[Dict],
    pool_side_effects: List[Dict],
    semaphore: asyncio.Semaphore,
    output_dir: Path,
    connectivity_instruction: str = "Generate 2-100 links (Default).",
    metadata: Dict[str, Any] = None
):
    """Generates a single gene and saves it."""
    async with semaphore:
        # Prepare Context
        # Sample mixing candidates (0-10) - Let's give a generous pool
        mix_sample = random.sample(pool_seeds, min(10, len(pool_seeds)))
        mix_str = ", ".join([s.get("name") for s in mix_sample])

        # Sample side effects (1-10) - Let's give a generous pool
        eff_sample = random.sample(pool_side_effects, min(10, len(pool_side_effects)))
        eff_str = ", ".join([e.get("name") for e in eff_sample])
        
        # ID Prefix for hallucination guidance
        id_prefix = gene_id.split("-")[0]

        # Format Prompt
        try:
            prompt_content = system_prompt_template.format(
                gene_id=gene_id,
                seed_name=seed_name,
                seed_description=seed_desc,
                side_effects_list=eff_str,
                mixing_candidates_list=mix_str,
                id_prefix=id_prefix,
                connectivity_instruction=connectivity_instruction
            )
        except KeyError as e:
            logger.error(f"Error formating prompt: Missing {e}")
            return

        # Call LLM
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # We use with_structured_output to enforce schema
                structured_llm = model.with_structured_output(MutatedGene)
                messages = [
                    ("system", prompt_content),
                    ("human", "Generate the gene record.")
                ]
                
                result: MutatedGene = await structured_llm.ainvoke(messages)
                
                # --- VALIDATION LOGIC ---
                valid_side_effects = {e.get("name") for e in pool_side_effects}
                
                # 1. Canonical Side Effects Check (Relaxed)
                invalid_effects = []
                for se in result.side_effect_profile:
                    # Check if se.side_effect matches any valid effect (exact or substring)
                    match = False
                    for valid in valid_side_effects:
                        # Case insensitive check & partial match flexibility
                        if valid.lower() in se.side_effect.lower() or se.side_effect.lower() in valid.lower():
                            match = True
                            # Auto-correction (Optional but good for data cleanliness)
                            se.side_effect = valid # Enforce canonical name
                            break
                    if not match:
                        invalid_effects.append(se.side_effect)
                        
                if invalid_effects:
                    logger.warning(f"  [Warning] Invalid side effects found: {invalid_effects}. Keeping them for creativity.")
                    # Relaxed validation: Allow them to pass (or we could filter them out)
                    # continue 
                    
                # 2. Connectivity Floor Check
                if len(result.regulated_genes) < 12:
                    logger.warning(f"  [Retry {attempt+1}/{max_retries}] Connectivity too low: {len(result.regulated_genes)} links (Min: 12)")
                    continue
                
                # --- SUCCESS ---
                # Save
                output_file = output_dir / f"{gene_id}.json"
                
                # Robustness: Handle ID collision if LLM returned a different ID or file exists
                # We enforce the ID passed in the prompt, but if result.gene_id differs, trust result but ensure filename matches 'gene_id'
                final_id = result.gene_id
                
                # Sanitize filename
                if metadata and "hero_name" in metadata:
                    # Use Hero Name: "Bugs Bunny" -> "bugs_bunny"
                    raw_name = metadata["hero_name"]
                    safe_filename = "".join(x for x in raw_name if x.isalnum() or x in (' ', '-', '_')).strip()
                    safe_filename = safe_filename.replace(" ", "_").lower()
                else:
                    safe_filename = "".join(x for x in final_id if x.isalnum() or x in ('-', '_')).strip()
                
                output_file = output_dir / f"{safe_filename}.json"
                
                # Simple collision avoidance
                counter = 1
                while output_file.exists():
                    output_file = output_dir / f"{safe_filename}_{counter}.json"
                    counter += 1
                    
                with open(output_file, "w") as f:
                    data_dict = result.model_dump()
                    if metadata:
                        data_dict.update(metadata)
                    f.write(json.dumps(data_dict, indent=2))
                    
                    f.write(json.dumps(data_dict, indent=2))
                    
                logger.info(f"  [Generated] {final_id} -> {output_file.name}")
                return # Done
                
            except Exception as e:
                logger.error(f"  [Error] Failed to generate {gene_id} (Attempt {attempt+1}): {e}")
                
        # If we exit the loop, we failed
        err_msg = f"Failed to generate gene {gene_id} after {max_retries} attempts."
        logger.error(f"  [Failure] {err_msg}")
        raise RuntimeError(err_msg)



async def main():
    # Load Config
    conf = get_app_conf("generate_powers")
    
    # Library
    library_seeds = conf.get_list("generate_powers.library.seeds")
    library_side_effects = conf.get_list("generate_powers.library.side_effects")
    
    # Settings
    genome_conf = conf.get_config("generate_genome.settings")
    concurrency = genome_conf.get_int("concurrency", 5)
    
    system_prompt = conf.get_string("generate_genome.system_prompt")
    
    stage_root = conf.get_string("stage_root")
    base_genome_dir = Path(stage_root) / "generated_genome"
    base_genome_dir.mkdir(parents=True, exist_ok=True)

    # Init Model
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        print("Error: OMGENE_OPEN_AI_API_KEY not set.")
        sys.exit(1)
    
    # Using slightly lower temp for structural consistency, 
    # but prompt should encourage creativity. 0.7-0.8 is good.
    model = ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=0.8)
    
    semaphore = asyncio.Semaphore(concurrency)
    
    # 1. Select Random Seeds
    selection_count = conf.get_int("generate_powers.vars.selection_count", 5)
    active_seeds = random.sample(library_seeds, min(selection_count, len(library_seeds)))
    
    print(f"Starting Genome Generation for {len(active_seeds)} Seeds...")
    
    tasks = []
    
    for seed in active_seeds:
        seed_name = seed.get("name")
        seed_desc = seed.get("description")
        
        # 2. Determine Batch Size (Skewed/Abnormal Distribution)
        # Weights: 70% small (1-5), 20% medium (6-20), 10% massive (21-50)
        dist_choice = random.choices(["small", "medium", "massive"], weights=[0.7, 0.2, 0.1], k=1)[0]
        
        if dist_choice == "small":
            num_genes = random.randint(1, 5)
        elif dist_choice == "medium":
            num_genes = random.randint(6, 20)
        else:
            num_genes = random.randint(21, 50)
            
        print(f"Seed '{seed_name}': Generating batch of {num_genes} genes ({dist_choice}).")
        
        # Prepare Directory
        seed_dir = base_genome_dir / seed_name.lower().replace(" ", "_")
        seed_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Create Tasks
        # Base ID part e.g. "FLIGHT"
        safe_seed_tag = "".join(x for x in seed_name if x.isalnum()).upper()[:6]
        
        
        for i in range(num_genes):
            # Generate ID: FLIGHT-829 (Random suffix to be ontology-like)
            suffix = random.randint(100, 999)
            gene_id = f"{safe_seed_tag}-{suffix}"
            
            # --- Connectivity Skew (Hub vs Leaf) ---
            # 85% Leaf (8-15 links), 15% Hub (30-50 links)
            is_hub = random.random() < 0.15
            if is_hub:
                min_links, max_links = 30, 50
                conn_type = "HUB"
            else:
                min_links, max_links = 15, 22
                conn_type = "LEAF"
                
            conn_instruction = f"Generate {min_links}-{max_links} links (Distribution: {conn_type})."
            
            tasks.append(
                generate_single_gene(
                    model, system_prompt, seed_name, seed_desc, gene_id,
                    library_seeds, library_side_effects, semaphore, seed_dir,
                    connectivity_instruction=conn_instruction
                )
            )
            
    # 4. Run All
    print(f"Queueing {len(tasks)} generation tasks...")
    await asyncio.gather(*tasks)
    print("Genome Generation Complete.")

if __name__ == "__main__":
    asyncio.run(main())
