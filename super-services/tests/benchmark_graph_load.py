import time
from pathlib import Path
from super.core.graph import GraphManager
import os

project_root = Path(__file__).resolve().parents[3] # super-services/src/super/apps/super_power_sage/ -> ... -> super-services
# Actually simpler: cwd is likely super-powers
warehouse_path = Path("data/warehouse").resolve()

def benchmark():
    print(f"Benchmarking GraphManager with warehouse: {warehouse_path}")
    
    # Measure Instantiation (Loading Parquet -> NetworkX)
    start = time.time()
    gm = GraphManager(warehouse_root=str(warehouse_path))
    init_time = time.time() - start
    print(f"GraphManager Init Time: {init_time:.4f}s")
    print(f"Graph Size: {gm.G.number_of_nodes()} nodes, {gm.G.number_of_edges()} edges")
    
    # Measure Subgraph Extraction (Bugs Bunny k=5)
    start = time.time()
    sub_G = gm.subgraph_for_hero("Bugs Bunny", depth=1, max_neighbors=5)
    subgraph_time = time.time() - start
    print(f"Subgraph (Bugs Bunny k=5) Extraction Time: {subgraph_time:.4f}s")
    
    # Measure Visualization (HTML Generation)
    start = time.time()
    html = gm.visualize(sub_G)
    viz_time = time.time() - start
    print(f"Visualization Generation Time: {viz_time:.4f}s")
    print(f"HTML Size: {len(html)/1024:.2f} KB")

    # Measure Overview Extraction
    start = time.time()
    ov_G = gm.get_overview_graph()
    overview_time = time.time() - start
    print(f"Overview Extraction Time: {overview_time:.4f}s")
    
    # Measure Overview Visualization
    start = time.time()
    html_ov = gm.visualize(ov_G)
    viz_ov_time = time.time() - start
    print(f"Overview Visualization Time: {viz_ov_time:.4f}s")

    print("-" * 30)
    print(f"Total Request Latency (Init + Viz): {init_time + subgraph_time + viz_time:.4f}s")

if __name__ == "__main__":
    benchmark()
