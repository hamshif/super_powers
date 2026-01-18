import pytest
from super.config import get_app_conf

def test_essentials_in_config():
    """Verify that essential runtime defaults are injected into the config."""
    conf = get_app_conf("generate_powers")
    
    # Check for project paths injection
    assert conf.get("project_root") is not None
    assert str(conf.get("project_root")).endswith("super_powers")
    
    assert conf.get("stage_root") is not None
    assert "stage" in str(conf.get("stage_root"))

def test_app_overrides():
    """Verify that app-specific config is loaded."""
    conf = get_app_conf("generate_powers")
    
    # Check strict config values from app.conf
    assert conf.get("generate_powers.seed") == "Flight"
    assert conf.get("generate_powers.n") == 20
