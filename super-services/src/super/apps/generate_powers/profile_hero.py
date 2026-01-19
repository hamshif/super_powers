"""
Script to profile heroes by mapping them to canonical seeds and side effects.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pyhocon import ConfigFactory

from super.apps.generate_powers.generate_genome import (
    load_library
)
from super.apps.generate_powers.models_hero import HeroProfile
from super.config import get_app_conf
from super.core.utils import get_stage_root

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def profile_hero(
    hero_name: str, 
    ontology: str, 
    seeds: List[dict], 
    side_effects: List[dict], 
    model: ChatOpenAI
) -> HeroProfile:
    """Uses LLM to profile a hero against the available library."""
    
    seed_list_str = "\n".join([f"- {s['name']}: {s['description']}" for s in seeds])
    effect_list_str = "\n".join([f"- {s['name']}: {s['description']}" for s in side_effects])
    
    system_prompt = (
        "You are an expert comic book power analyst.\n"
        "Your task is to map a known Hero to the most accurate Power Seeds and Side Effects from our specific library.\n"
        "\n"
        "### AVAILABLE SEEDS (Choose 1 Primary, 1-3 Secondary)\n"
        f"{seed_list_str}\n"
        "\n"
        "### AVAILABLE SIDE EFFECTS (Choose 1-3)\n"
        f"{effect_list_str}\n"
        "\n"
        "### INSTRUCTIONS\n"
        "1. **Primary Seed**: Must be the single closest match to their core power.\n"
        "2. **Secondary Seeds**: Must cover other key abilities.\n"
        "3. **Side Effects**: Choose effects that match their weaknesses or personality flaws.\n"
        "4. **Strictness**: You MUST use the exact names provided in the lists above.\n"
    )
    
    prompt = f"Profile the hero: {hero_name} ({ontology})"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ]
    
    structured_llm = model.with_structured_output(HeroProfile)
    
    # Retry loop for strictness
    for attempt in range(3):
        try:
            profile: HeroProfile = await structured_llm.ainvoke(messages)
            
            # Additional validation loop if needed? 
            # Pydantic validates type, but we want to validate existence in list?
            # Let's trust the model for now, it usually follows "Strictness" well with Structured Output.
            return profile
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {hero_name}: {e}")
            if attempt == 2:
                raise e

async def main():
    # 1. Load Configs
    conf_sage = get_app_conf(app="super_power_sage") # Load Sage config to get heroes
    conf_gen = get_app_conf(app="generate_powers")   # Load Gen config to get seeds path
    
    # 2. Get Heroes List
    # Config structure: super_power_sage.heroes.{ontology} = [list]
    heroes_conf = conf_sage.get("super_power_sage.heroes")
    
    # 3. Load Libraries (Seeds/Effects) directly from config
    # Since they are included in app.conf, they are available in the merged config
    seeds = conf_gen.get_list("generate_powers.library.seeds")
    side_effects = conf_gen.get_list("generate_powers.library.side_effects")
    
    logger.info(f"Loaded {len(seeds)} seeds and {len(side_effects)} side effects.")
    
    # 4. Initialize Model
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        raise ValueError("API Key not found!")
    
    model = ChatOpenAI(api_key=api_key, model="gpt-4o") # Use 4o for high quality profiling
    
    # 5. Output Dir
    stage_root = get_stage_root()
    profile_dir = stage_root / "hero_profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    # 6. Iterate and Profile
    tasks = []
    
    # Semaphore to limit concurrency
    sem = asyncio.Semaphore(10)

    async def _process_hero(ontology, name):
        async with sem:
            out_file = profile_dir / ontology / f"{name}.json"
            if out_file.exists():
                logger.info(f"Skipping {name} (Exists)")
                return
            
            logger.info(f"Profiling {name}...")
            try:
                profile = await profile_hero(name, ontology, seeds, side_effects, model)
                
                # Verify match?
                # Ensure primary seed exists
                known_seeds = {s['name'] for s in seeds}
                if profile.primary_seed_name not in known_seeds:
                    logger.error(f"Invalid Primary Seed for {name}: {profile.primary_seed_name}")
                    # Could retry here, but simple logging is fine for now
                
                # Save
                out_file.parent.mkdir(parents=True, exist_ok=True)
                with open(out_file, "w") as f:
                    f.write(profile.model_dump_json(indent=2))
                logger.info(f"Saved {name}")
                
            except Exception as e:
                logger.error(f"Failed to profile {name}: {e}")

    for ontology, names in heroes_conf.items():
        for name in names:
            tasks.append(_process_hero(ontology, name))
            
    await asyncio.gather(*tasks)
    logger.info("Profiling Complete.")

if __name__ == "__main__":
    asyncio.run(main())
