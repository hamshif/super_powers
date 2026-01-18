
"""
CLI entry point for the Generate Powers app.
"""
import argparse
import asyncio
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
    # Load configuration - Let it fail if missing per AGENTS.md
    conf = get_app_conf("generate_powers")
    
    seeds = conf.get_list("generate_powers.seeds")
    n = conf.get_int("generate_powers.n")
    temperature = conf.get_float("generate_powers.temperature", 0.7)
    system_prompt = conf.get_string("generate_powers.system_prompt")

    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        print("Error: OMGENE_OPEN_AI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
        
    model = ChatOpenAI(api_key=api_key, model="gpt-4o", temperature=temperature)
    graph = ExpansionGraphFactory.create_graph(model, system_prompt)
    
    for seed in seeds:
        print(f"Generating {n} variants for seed '{seed}' (Temp: {temperature})...")
        
        try:
            inputs = {"seed": seed, "n": n, "messages": []}
            result_state = await graph.ainvoke(inputs)
            
            # Extract the result from the state
            if "result" in result_state:
                result_obj: ExpansionResult = result_state["result"]
                
                # FILE OUTPUT LOGIC
                stage_root = conf.get_string("stage_root")
                
                # Create parent output dir comprised of query_vars
                # Sanitize seed for path
                safe_seed = "".join(x for x in seed if x.isalnum() or x in (' ', '_', '-')).strip().replace(' ', '_').lower()
                query_vars_dir = f"{safe_seed}_n{n}_t{temperature}"
                
                output_dir = Path(stage_root) / "generated_powers" / query_vars_dir
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / f"{safe_seed}.json"
                
                # Generate JSON Output
                formatted_output = result_obj.model_dump_json(indent=2)
                
                with open(output_file, "w") as f:
                    f.write(formatted_output)
                    
                print(f"Successfully generated powers for '{seed}'.")
                print(f"Output written to: {output_file}")

            else:
                print(f"Error: Graph did not return a result for seed '{seed}'.", file=sys.stderr)
                
        except Exception as e:
            print(f"Error generating powers for '{seed}': {e}", file=sys.stderr)
            # Continue to next seed instead of exiting?
            # User might want to stop, but for batch processing usually continue is better.
            # let's continue.
            continue

if __name__ == "__main__":
    asyncio.run(main())
