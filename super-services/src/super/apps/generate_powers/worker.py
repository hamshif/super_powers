
import asyncio
import logging
import ray
from super.apps.generate_powers import generate_heroes
from super.core.utils import get_stage_root, get_app_conf, get_valid_llm
from super.apps.generate_powers.models_hero import HeroProfile

logger = logging.getLogger(__name__)

@ray.remote
class HeroGenerator:
    """
    Ray Actor to manage hero generation tasks consistently.
    """
    def __init__(self):
        # Load Resources once per actor
        self.conf = get_app_conf(app="generate_powers")
        self.system_prompt = self.conf.get_string("generate_genome.system_prompt")
        
        # Load Libraries
        seeds = self.conf.get_list("generate_powers.library.seeds")
        side_effects = self.conf.get_list("generate_powers.library.side_effects")
        self.seed_map = {s['name']: s for s in seeds}
        self.effect_map = {e['name']: e for e in side_effects}
        
        # Init Model
        self.model = get_valid_llm(model_name="gpt-4o", temperature=0.8)
        self.semaphore = asyncio.Semaphore(5) # Allow some concurrency in the actor?
        
        # Paths
        self.stage_root = get_stage_root()
        self.output_dir_base = self.stage_root / "hero_genomes"
        
        logging.info("HeroGenerator Actor Initialized.")

    async def generate_hero(self, hero_name: str, ontology: str) -> str:
        """
        Generates a hero's genome. 
        Returns a status string.
        """
        try:
            logger.info(f"Actor starting generation for {hero_name} ({ontology})...")
            
            # Check if seed exists in current map, if not reload config to be safe
            # This handles runtime updates to seeds.conf without actor restart
            profile_seed = None # We need to peek at the profile or just reload blindly?
            # We don't have the profile here yet, we only have hero_name. 
            # But process_hero loads the profile. 
            # So let's just reload config here to be safe, or peek.
            # Efficiency: Reloading config is cheap compared to LLM.
            
            # Reload Config & Library
            self.conf = get_app_conf(app="generate_powers")
            seeds = self.conf.get_list("generate_powers.library.seeds")
            side_effects = self.conf.get_list("generate_powers.library.side_effects")
            self.seed_map = {s['name']: s for s in seeds}
            self.effect_map = {e['name']: e for e in side_effects}
            
            # Create Output Dir
            output_ontology_dir = self.output_dir_base / ontology
            output_ontology_dir.mkdir(parents=True, exist_ok=True)

            res = await generate_heroes.generate_single_hero(
                 hero_name=hero_name,
                 ontology=ontology,
                 model=self.model,
                 system_prompt=self.system_prompt,
                 seed_map=self.seed_map,
                 effect_map=self.effect_map,
                 stage_root=self.stage_root,
                 output_dir=output_ontology_dir,
                 semaphore=self.semaphore
            )
            return f"Generation complete for {hero_name}. Result: {res}"

        except Exception as e:
            logger.error(f"Error in HeroGenerator: {e}", exc_info=True)
            return f"Error generating {hero_name}: {str(e)}"
