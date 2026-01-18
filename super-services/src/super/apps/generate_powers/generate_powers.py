
"""
CLI entry point for the Generate Powers app.
"""
import argparse
import asyncio
import os
import sys

from langchain_openai import ChatOpenAI
from rich.console import Console

# Adjust path to include src to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../src"))

from super.apps.generate_powers.agent import ExpansionGraphFactory
from super.apps.generate_powers.models import ExpansionResult
from super.config import get_app_conf

from super.config import get_app_conf

from pyhocon import ConfigFactory, HOCONConverter

def convert_to_hocon_str(result: ExpansionResult) -> str:
    """Converts the ExpansionResult to a HOCON string using the pyhocon library."""
    
    # reshaping to target structure
    gradient_dict = {
        variant.name: {"description": variant.description}
        for variant in result.gradient
    }
    
    structure = {
        "abilities": {
            result.seed_name: {
                "description": result.seed_description,
                "gradient": gradient_dict
            }
        }
    }
    
    conf = ConfigFactory.from_dict(structure)
    return HOCONConverter.to_hocon(conf)

async def main():
    # Load configuration
    try:
        conf = get_app_conf("generate_powers")
        # Strict loading: No defaults provided, will raise error if missing
        seed = conf.get_string("generate_powers.seed")
        n = conf.get_int("generate_powers.n")
        output_format = conf.get_string("generate_powers.format", "hocon")
        
    except Exception as e:
        print(f"Configuration Error: Missing required config keys in app.conf: {e}", file=sys.stderr)
        sys.exit(1)
    
    api_key = os.getenv("OMGENE_OPEN_AI_API_KEY")
    if not api_key:
        print("Error: OMGENE_OPEN_AI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Generating {n} variants for seed '{seed}'...")
    
    model = ChatOpenAI(api_key=api_key, model="gpt-4o")
    graph = ExpansionGraphFactory.create_graph(model)
    
    try:
        inputs = {"seed": seed, "n": n, "messages": []}
        result_state = await graph.ainvoke(inputs)
        
        # Extract the result from the state
        if "result" in result_state:
            result_obj: ExpansionResult = result_state["result"]
            
            if output_format.lower() == "json":
                print(result_obj.model_dump_json(indent=2))
            else:
                formatted_output = convert_to_hocon_str(result_obj)
                print(formatted_output)
        else:
            print("Error: Graph did not return a result.", file=sys.stderr)
            
    except Exception as e:
        print(f"Error generating powers: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
