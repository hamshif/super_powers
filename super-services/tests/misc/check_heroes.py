import os
import pandas as pd
from super.apps.super_power_sage.tools import _get_warehouse_root

def check_heroes():
    root = _get_warehouse_root()
    print(f"Warehouse root: {root}")
    
    profiles_path = os.path.join(root, "hero_profiles")
    if not os.path.exists(profiles_path):
        print("Hero profiles not found.")
        return

    df = pd.read_parquet(profiles_path)
    print(f"Total heroes: {len(df)}")
    
    # Check for "Bunny"
    bunnies = df[df['hero_name'].str.contains("Bunny", case=False, na=False)]
    if not bunnies.empty:
        print("Found matching 'Bunny':")
        print(bunnies['hero_name'].tolist())
    else:
        print("No heroes with 'Bunny' found.")

if __name__ == "__main__":
    check_heroes()
