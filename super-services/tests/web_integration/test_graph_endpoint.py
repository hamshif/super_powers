import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from super.apps.super_power_sage.super_power_sage import app
from super.core.graph import GraphManager

client = TestClient(app)

def test_visualize_graph_overview():
    """Verify that the overview endpoint returns HTML."""
    # Mock GraphManager
    mock_gm_instance = MagicMock()
    mock_gm_instance.visualize.return_value = "<html><body>Mock Graph</body></html>"
    mock_gm_instance.get_overview_graph.return_value = MagicMock()
    
    # We explicitly patch the class where it's imported/used.
    # IN super_power_sage.py, we do: `from super.core.graph import GraphManager` inside the function.
    # So we should patch `super.core.graph.GraphManager` class.
    # Wait, if it imports it inside the function, patching 'super.core.graph.GraphManager' globally works 
    # IF the module hasn't already imported it differently.
    # The code says: `from super.core.graph import GraphManager` inside the func.
    # So `with patch('super.core.graph.GraphManager')` should work.
    
    with patch('super.core.graph.GraphManager', return_value=mock_gm_instance) as MockGM:
        response = client.get("/super_powers_sage/visualize_graph")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Mock Graph" in response.text
        
        # Verify get_overview_graph was called on the INSTANCE
        mock_gm_instance.get_overview_graph.assert_called_once()

def test_visualize_graph_hero_context():
    """Verify that the endpoint handles hero context."""
    mock_gm_instance = MagicMock()
    mock_gm_instance.visualize.return_value = "<html><body>Mock Hero Graph</body></html>"
    mock_gm_instance.subgraph_for_hero.return_value = MagicMock()
    
    with patch('super.core.graph.GraphManager', return_value=mock_gm_instance) as MockGM:
        response = client.get("/super_powers_sage/visualize_graph?center=Superman")
        
        assert response.status_code == 200
        assert "Mock Hero Graph" in response.text
        
        # Verify subgraph_for_hero was called with 'Superman'
        mock_gm_instance.subgraph_for_hero.assert_called_with("Superman", depth=2)
