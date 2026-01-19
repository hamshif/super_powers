import sys
import os
import networkx as nx

# Add src to path
sys.path.append(os.path.abspath('../super-services/src'))

from super.core.graph import GraphManager

# Initialize GraphManager
warehouse_path = os.path.abspath('../data/warehouse')
print(f"Loading warehouse from: {warehouse_path}")
gm = GraphManager(warehouse_root=warehouse_path)
print(f"Graph Created! Nodes: {gm.G.number_of_nodes()}, Edges: {gm.G.number_of_edges()}")

# Query Flying Heroes
flying_heroes = gm.get_flying_heroes()
print(f"Flying Heroes found: {len(flying_heroes)}")

if flying_heroes:
    hero = flying_heroes[0]
    print(f"Visualizing subgraph for {hero}...")
    sub_G = gm.subgraph_for_hero(hero, depth=2)
    if sub_G:
        outfile = f"reproduce_graph_{hero.replace(' ', '_')}.html"
        # We simulate the notebook call
        res = gm.visualize(sub_G, filename=outfile)
        print(f"Visualization saved to {outfile}")
        
        # Check file size
        if os.path.exists(outfile):
            size = os.path.getsize(outfile)
            print(f"File size: {size} bytes")
            if size < 100:
                print("WARNING: File seems too small.")
                with open(outfile, 'r') as f:
                    print(f.read())
        else:
            print("ERROR: File was not created.")
