
import os
import networkx as nx
import pandas as pd
from pyvis.network import Network

class GraphManager:
    """
    Manages the Knowledge Graph for Super Powers, Genes, and Heroes.
    Loads data from the Warehouse and builds an in-memory NetworkX graph.
    """

    def __init__(self, warehouse_root=None):
        if not warehouse_root:
            # Default location relative to this file? 
            # Assuming standard layout: src/super/core/graph.py -> ../../../data/warehouse
            # But safer to use the one passed or default to same logic as warehouse.py
            # For now, let's look for env var or specific path
             self.warehouse_root = os.getenv("WAREHOUSE_ROOT", os.path.abspath(os.path.join(os.getcwd(), "../../data/warehouse")))
        else:
             self.warehouse_root = warehouse_root

        self.G = nx.MultiDiGraph() # Directed graph with multiple edges possible
        self._load_data_and_build()

    def _load_data_and_build(self):
        """Loads all Parquet entities and constructs the graph."""
        
        # --- 1. Load DataFrames ---
        # Helper to load safely
        def load(name):
            path = os.path.join(self.warehouse_root, name)
            if os.path.exists(path):
                return pd.read_parquet(path)
            return pd.DataFrame()

        heroes_df = load("hero_profiles")
        genes_df = load("genes")
        # hero_genes: linking table
        hero_genes_df = load("hero_genes") 
        powers_df = load("powers")
        
        # Seeds
        gene_seeds_df = load("gene_seeds")
        hero_seeds_df = load("hero_profile_seeds")
        power_seeds_df = load("power_seeds")
        
        # Regulations & Effects
        regulations_df = load("hero_gene_regulation")
        gene_side_effects_df = load("gene_side_effects")
        hero_side_effects_df = load("hero_profile_side_effects")

        # --- 2. Add Nodes ---
        
        # Heroes
        for _, row in heroes_df.iterrows():
            self.G.add_node(
                row['hero_name'], 
                type='Hero', 
                bio=row.get('bio', ''), 
                ontology=row.get('ontology', '')
            )
            
        # Genes (using gene_id)
        # We use explicit genes_df for metadata, but hero_genes might have extra genes?
        # Let's rely on genes_df for the main definition, but add any from hero_genes if missing
        if not genes_df.empty:
            for _, row in genes_df.iterrows():
                self.G.add_node(
                    row['gene_id'],
                    type='Gene',
                    mutation_class=row.get('mutation_class', ''),
                    role=row.get('gene_role', '')
                )
                
        # Powers
        if not powers_df.empty:
            for _, row in powers_df.iterrows():
                # Use Power Name as ID if unique, or ID? 
                # IDs are UUIDs like '9331c703ce3b'. Names are readable. 
                # Interactive graph is better with readable names. 
                # Let's use ID as node ID, but add clean label.
                pid = row['power_id']
                self.G.add_node(
                    pid,
                    label=row['power_name'],
                    type='Power',
                    description=row.get('description', '')
                )
                
        # Side Effects (Name as ID)
        if not gene_side_effects_df.empty:
            for se in gene_side_effects_df['side_effect_name'].unique():
                self.G.add_node(se, type='SideEffect')
        if not hero_side_effects_df.empty:
             for se in hero_side_effects_df['side_effect_name'].unique():
                self.G.add_node(se, type='SideEffect')
                
        # Seeds (Name as ID)
        # Aggregate all seed names
        all_seeds = set()
        if not gene_seeds_df.empty: all_seeds.update(gene_seeds_df['seed_name'].unique())
        if not hero_seeds_df.empty: all_seeds.update(hero_seeds_df['seed_name'].unique())
        if not power_seeds_df.empty: all_seeds.update(power_seeds_df['seed_name'].unique())
        
        for s in all_seeds:
            self.G.add_node(s, type='Seed', color='#ffff00') # Visual hint

        # --- 3. Add Edges ---
        
        # Hero -> Gene
        if not hero_genes_df.empty:
            for _, row in hero_genes_df.iterrows():
                if row['hero_name'] in self.G and row['gene_id'] in self.G:
                    self.G.add_edge(row['hero_name'], row['gene_id'], relation='HAS_GENE')

        # Gene -> SideEffect
        if not gene_side_effects_df.empty:
             for _, row in gene_side_effects_df.iterrows():
                 if row['gene_id'] in self.G:
                     self.G.add_edge(
                         row['gene_id'], 
                         row['side_effect_name'], 
                         relation='CAUSES_SIDE_EFFECT',
                         trigger=row.get('trigger_condition', '')
                     )
                     
        # Hero -> SideEffect
        if not hero_side_effects_df.empty:
             for _, row in hero_side_effects_df.iterrows():
                 if row['hero_name'] in self.G:
                     self.G.add_edge(
                         row['hero_name'], 
                         row['side_effect_name'], 
                         relation='SUFFERS_SIDE_EFFECT'
                     )

        # Gene Regulation (Gene -> Gene)
        if not regulations_df.empty:
            for _, row in regulations_df.iterrows():
                src = row['source_gene_id']
                dst = row['target_gene_id']
                # Only add if both exist (though we could lazy add)
                if src in self.G and dst in self.G:
                    self.G.add_edge(
                        src, dst, 
                        relation='REGULATES', 
                        hero=row.get('hero_name', 'Global'),
                        effect=row.get('effect', ''),
                        strength=row.get('strength', 0.0)
                    )

        # SEED LINKS (The glue)
        # Hero -> Seed
        if not hero_seeds_df.empty:
            for _, row in hero_seeds_df.iterrows():
                if row['hero_name'] in self.G:
                    self.G.add_edge(row['hero_name'], row['seed_name'], relation='SOURCED_FROM')
                    
        # Seed -> Gene
        if not gene_seeds_df.empty:
            for _, row in gene_seeds_df.iterrows():
                if row['gene_id'] in self.G:
                     # Usually Seed -> Gene (Seed creates Gene)
                     self.G.add_edge(row['seed_name'], row['gene_id'], relation='GENERATES_GENE')
                     
        # Seed -> Power
        if not power_seeds_df.empty:
            for _, row in power_seeds_df.iterrows():
                if row['power_id'] in self.G:
                    self.G.add_edge(row['seed_name'], row['power_id'], relation='GENERATES_POWER')

    def get_flying_heroes(self):
        """Returns list of heroes with 'fly' or 'flight' in their data or connected components."""
        # Method 1: Search Bio
        heroes = []
        for n, data in self.G.nodes(data=True):
            if data.get('type') == 'Hero':
                if 'fly' in data.get('bio', '').lower() or 'flight' in data.get('bio', '').lower():
                    heroes.append(n)
        return heroes

    def subgraph_for_hero(self, hero_name, depth=2):
        """Extracts a subgraph centered on a hero."""
        if hero_name not in self.G:
            return None
        
        nodes = {hero_name}
        curr = {hero_name}
        for _ in range(depth):
            next_nodes = set()
            for n in curr:
                # Neighbors (both directions)
                neighbors = set(self.G.successors(n)) | set(self.G.predecessors(n))
                next_nodes.update(neighbors)
            nodes.update(next_nodes)
            curr = next_nodes
            
        return self.G.subgraph(nodes)

    def visualize(self, graph=None, filename=None):
        """
        Visualizes the graph using PyVis.
        
        Args:
            graph (nx.Graph, optional): Subgraph to visualize. Defaults to full graph.
            filename (str, optional): If provided, saves HTML to this file. 
                                      If None, returns the HTML string for inline display.
        """
        if graph is None:
            graph = self.G
            
        net = Network(height="750px", width="100%", notebook=True, cdn_resources='in_line')
        net.from_nx(graph)
        
        # Color nodes by type
        for node in net.nodes:
            ntype = node.get('type', 'Unknown')
            if ntype == 'Hero': node['color'] = '#ff9999' # Red
            elif ntype == 'Gene': node['color'] = '#99ff99' # Green
            elif ntype == 'Power': node['color'] = '#9999ff' # Blue
            elif ntype == 'Seed': node['color'] = '#ffff99' # Yellow
            elif ntype == 'SideEffect': node['color'] = '#ffcc99' # Orange
            
        net.show_buttons(filter_=['physics'])
        
        if filename:
            net.show(filename)
            return filename
        else:
            # Return HTML string for inline display
            # net.generate_html() returns the HTML string
            return net.generate_html()
