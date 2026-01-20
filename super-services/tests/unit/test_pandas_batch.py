
import os
import pandas as pd
from super.core import utils
from super.core.warehouse import get_all_heroes_data

def verify_batch():
    # Load config to get correct path
    conf = utils.get_app_conf("generate_powers")
    stage_root = conf.get_string("stage_root")
    warehouse_root = os.path.join(stage_root, "warehouse")
    
    ontology = "Looney Tunes"
    print(f"Testing Batch Retrieval for '{ontology}' from {warehouse_root}...")
    
    df = get_all_heroes_data(warehouse_root=warehouse_root, ontology=ontology)
    
    if not df.empty:
        print(f"✅ Retrieved {len(df)} heroes.")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Sample Hero: {df.iloc[0]['hero_name']}")
        print(f"   Sample Cluster Summary: {df.iloc[0]['cluster_network_summary'][:50]}...")
    else:
        print(f"❌ No data found for {ontology}!")

if __name__ == "__main__":
    verify_batch()
