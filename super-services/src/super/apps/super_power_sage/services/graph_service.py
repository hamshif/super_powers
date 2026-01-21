
import ray
import logging
from typing import Optional
from pathlib import Path
from super.core.graph import GraphManager

logger = logging.getLogger(__name__)

@ray.remote
class GraphService:
    def __init__(self, warehouse_root: str, default_hero: str, default_neighbors: int):
        self.warehouse_root = warehouse_root
        self.default_hero = default_hero
        self.default_neighbors = default_neighbors
        self.gm: Optional[GraphManager] = None
        self._initialize()

    def _initialize(self):
        try:
            logger.info(f"GraphService initializing with warehouse: {self.warehouse_root}")
            self.gm = GraphManager(warehouse_root=self.warehouse_root)
            logger.info(f"GraphService initialized. Nodes: {self.gm.G.number_of_nodes()}")
        except Exception as e:
            logger.error(f"GraphService failed to initialize GraphManager: {e}")
            raise e

    def get_html(self, center: Optional[str]) -> str:
        """
        Returns the HTML string for the requested graph center.
        This runs in a separate process, so blocking IO/CPU here doesn't freeze FastAPI.
        """
        if self.gm is None:
            return "<h1>Graph Service Unavailable</h1>"

        sub_G = None
        use_physics = True
        
        # 1. Default View
        if not center:
            logger.info(f"Generating Default Graph: {self.default_hero} (k={self.default_neighbors})")
            sub_G = self.gm.subgraph_for_hero(self.default_hero, depth=1, max_neighbors=self.default_neighbors)
            if sub_G is None or sub_G.number_of_nodes() == 0:
                 sub_G = self.gm.get_overview_graph() # Fallback
                 use_physics = False # Overview fallback is large

        # 2. Overview
        elif center.lower() in ["overview", "global overview"]:
             logger.info("Generating Overview Graph")
             sub_G = self.gm.get_overview_graph()
             use_physics = False # Disable physics for Overview to prevent blocking
             
        # 3. Contextual
        else:
            logger.info(f"Generating Subgraph: {center}")
            sub_G = self.gm.subgraph_for_hero(center, depth=2)
            
        if sub_G is None:
             return "<h1>Graph not found</h1>"
             
        # Generate HTML (CPU Heavy)
        return self.gm.visualize(sub_G, physics_enabled=use_physics)

    def get_graph_data(self, center: Optional[str]) -> dict:
        """
        Returns JSON data (nodes/edges) for frontend rendering.
        """
        if self.gm is None:
            return {"nodes": [], "edges": [], "error": "Graph Service Unavailable"}

        sub_G = None
        
        # 1. Default View
        if not center:
            sub_G = self.gm.subgraph_for_hero(self.default_hero, depth=1, max_neighbors=self.default_neighbors)
            if sub_G is None or sub_G.number_of_nodes() == 0:
                 sub_G = self.gm.get_overview_graph() # Fallback

        # 2. Overview
        elif center.lower() in ["overview", "global overview"]:
             sub_G = self.gm.get_overview_graph()
             
        # 3. Contextual
        else:
            sub_G = self.gm.subgraph_for_hero(center, depth=2)
            
        if sub_G is None:
             return {"nodes": [], "edges": [], "error": "Graph not found"}
             
        # Return JSON Data
        return self.gm.get_visualization_data(sub_G)
