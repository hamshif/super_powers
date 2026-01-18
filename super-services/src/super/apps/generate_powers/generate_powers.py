
"""
CLI entry point for the Generate Powers app.
import random
"""
import random
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from rich.console import Console



from super.apps.generate_powers.agent import ExpansionGraphFactory
from super.apps.generate_powers.models import ExpansionResult
from super.config import get_app_conf

from super.config import get_app_conf

from pyhocon import ConfigFactory


async def main():
    # Load configuration
    conf = get_app_conf("generate_powers")
    
    # Load Libraries
    library_seeds = conf.get_list("generate_powers.library.seeds")
    library_side_effects = conf.get_list("generate_powers.library.side_effects")
    
    n = conf.get_int("generate_powers.n")
    temperature = conf.get_float("generate_powers.temperature", 0.7)
    
    raw_system_prompt_template = conf.get_string("generate_powers.system_prompt")
    
    # Load control vars
    template_vars = conf.get_config("generate_powers.vars").as_plain_ordered_dict()
    
    selection_count = int(template_vars.get("selection_count", 5))
    mix_min = int(template_vars.get("mixing_min", 0))
    mix_max = int(template_vars.get("mixing_max", 3))
    eff_min = int(template_vars.get("side_effect_min", 0))
    eff_max = int(template_vars.get("side_effect_max", 3))

    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        print("Error: OMGENE_OPEN_AI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
        
    model = ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=temperature)
    
    # Stochastic Selection of Seeds
    # Ensure we don't sample more than available
    count = min(selection_count, len(library_seeds))
    active_seeds = random.sample(library_seeds, count)
    
    print(f"Selected {len(active_seeds)} random seeds from library (Total {len(library_seeds)}).")
    
    stage_root = conf.get_string("stage_root")
    
    for seed_obj in active_seeds:
        seed_name = seed_obj.get("name")
        seed_desc = seed_obj.get("description")
        
        # Determine mixing candidates (from OTHER library seeds)
        other_seeds = [s for s in library_seeds if s.get("name") != seed_name]
        
        mix_count = random.randint(mix_min, mix_max)
        mix_candidates = random.sample(other_seeds, min(mix_count, len(other_seeds)))
        mix_str = ", ".join([s.get("name") for s in mix_candidates]) if mix_candidates else "None"
        
        # Determine side effects
        eff_count = random.randint(eff_min, eff_max)
        active_effects = random.sample(library_side_effects, min(eff_count, len(library_side_effects)))
        eff_str = ", ".join([f"{e.get('name')}" for e in active_effects]) if active_effects else "None" # Only name for brevity in prompt list, or name+desc?
        # User prompt example showed just "Hubris". But description is useful. Let's use Name for list, maybe Name+Desc is better for context.
        # "Consider integrating these themes... [Hubris, ...]". If I just give name, model knows? No.
        # I should provide descriptions.
        eff_context = ", ".join([f"{e.get('name')}: {e.get('description')}" for e in active_effects]) if active_effects else "None"

        print(f"Generating {n} variants for '{seed_name}'...")
        print(f"  Mixing: {mix_str}")
        print(f"  Side Effects: {eff_count}")
        
        # Prepare context for prompt
        current_vars = template_vars.copy()
        current_vars["seed_name"] = seed_name
        current_vars["seed_description"] = seed_desc
        current_vars["mixing_candidates_list"] = mix_str
        current_vars["side_effects_list"] = eff_context
        
        # Capture instructions for JSON
        creation_instructions = {
            "seed_name": seed_name,
            "seed_description": seed_desc,
            "model_temperature": temperature,
            "mixing_candidates": [s.get("name") for s in mix_candidates],
            "side_effects": [e.get("name") for e in active_effects],
            "config_vars": current_vars
        }
        
        # Inject variables
        try:
            system_prompt = raw_system_prompt_template.format(**current_vars)
        except KeyError as e:
            print(f"Error: Prompt placeholder {e} missing.", file=sys.stderr)
            continue

        graph = ExpansionGraphFactory.create_graph(model, system_prompt)
        
        try:
            inputs = {"seed": seed_name, "n": n, "messages": []}
            result_state = await graph.ainvoke(inputs)
            
            if "result" in result_state:
                result_obj: ExpansionResult = result_state["result"]
                
                # Convert to dict and attach creation instructions
                output_data = result_obj.model_dump()
                output_data["creation_instructions"] = creation_instructions
                
                # Auto-increment file output
                safe_seed = "".join(x for x in seed_name if x.isalnum() or x in (' ', '_', '-')).strip().replace(' ', '_').lower()
                base_output_dir = Path(stage_root) / "generated_powers" / safe_seed
                base_output_dir.mkdir(parents=True, exist_ok=True)
                
                # Find next run ID
                run_id = 1
                while (base_output_dir / f"run_{run_id}.json").exists():
                    run_id += 1
                
                output_file = base_output_dir / f"run_{run_id}.json"
                
                with open(output_file, "w") as f:
                    json.dump(output_data, f, indent=2)
                    
                print(f"  Success. Output: {output_file}")

            else:
                print(f"  Error: No result for '{seed_name}'.", file=sys.stderr)
                
        except Exception as e:
            print(f"  Error processing '{seed_name}': {e}", file=sys.stderr)
            continue

if __name__ == "__main__":
    asyncio.run(main())
