"""
Sanity check script to verify configuration loading.
Prints the merged configuration for the 'generate_powers' app.
"""
import sys
import os


from super.config import get_app_conf
from pyhocon import HOCONConverter

def main():
    print("Loading configuration for app='generate_powers'...")
    try:
        conf = get_app_conf("generate_powers")
        
        # Verify Critical Injections
        print("\n--- Critical Paths ---")
        print(f"project_root: {conf.get('project_root', 'MISSING')}")
        print(f"stage_root:   {conf.get('stage_root', 'MISSING')}")
        
        # Verify App Specifics
        print("\n--- App Config ---")
        print(f"seed:         {conf.get('generate_powers.seed', 'MISSING')}")
        print(f"n:            {conf.get('generate_powers.n', 'MISSING')}")
        
        # Full Dump
        print("\n--- Full Merged Config (HOCON) ---")
        print(HOCONConverter.to_hocon(conf))
        
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
