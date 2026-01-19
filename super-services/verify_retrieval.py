
import os
import time
from super.core import utils
from super.core.warehouse import get_hero_data

def verify():
    # Load config to get correct path
    conf = utils.get_app_conf("generate_powers")
    stage_root = conf.get_string("stage_root")
    warehouse_root = os.path.join(stage_root, "warehouse")
    
    print(f"Testing Single Hero Retrieval (Pandas) from {warehouse_root}...")
    
    start = time.time()
    # 1. Targeted Lookup (Partition Pruning)
    # The ontology on disk is Title Case "Looney Tunes", not snake_case
    hero = get_hero_data("Bugs Bunny", ontology="Looney Tunes", warehouse_root=warehouse_root)
    duration = (time.time() - start) * 1000
    
    if hero:
        print(f"✅ Found Hero: {hero['hero_name']}")
        print(f"   Ontology: {hero['ontology']}")
        print(f"   Master Gene: {hero.get('master_gene', {}).get('gene_id')}")
        print(f"   Cluster Size: {hero.get('cluster_size')}")
        print(f"   Latency: {duration:.2f}ms")
    else:
        print("❌ Bugs Bunny not found!")

    print("-" * 20)
    
    # 2. Broad Lookup (No Partition)
    print("Testing Broad Lookup (Scan All)...")
    start = time.time()
    hero_broad = get_hero_data("Iron Man", warehouse_root=warehouse_root) # Should be in marvel
    duration = (time.time() - start) * 1000
    
    if hero_broad:
        print(f"✅ Found Hero: {hero_broad['hero_name']}")
        print(f"   Ontology: {hero_broad['ontology']}")
        print(f"   Latency: {duration:.2f}ms")
    else:
        print("❌ Iron Man not found!")

if __name__ == "__main__":
    verify()
