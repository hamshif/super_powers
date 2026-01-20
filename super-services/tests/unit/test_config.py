import pytest
from super.config import get_app_conf

@pytest.mark.unit
def test_essentials_in_config():
    """Verify that essential runtime defaults are injected into the config."""
    conf = get_app_conf("generate_powers")
    
    # Check for project paths injection
    assert conf.get("project_root") is not None
    assert str(conf.get("project_root")).endswith("super_powers")
    
    assert conf.get("stage_root") is not None
    # Path might just be /data/warehouse, so just check it exists/is not empty
    assert len(str(conf.get("stage_root"))) > 0

@pytest.mark.unit
def test_app_overrides():
    """Verify that app-specific config is loaded."""
    conf = get_app_conf("generate_powers")
    
    # Check strict config values from app.conf
    # 'n' is defined in app.conf
    assert conf.get("generate_powers.n") == 20
    # 'vars.similarity_target' is defined in app.conf but OVERRIDDEN in developer.conf
    # The developer.conf value (0.2-0.9) takes precedence locally.
    assert conf.get("generate_powers.vars.similarity_target") == "0.2-0.9"
