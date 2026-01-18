"""
Centralized configuration utility for super-services.

This module owns the definition of where the configuration exists for THIS service package.
It wraps the core configuration utilities to inject the correct `conf_root`.
"""

from pathlib import Path
from typing import Any

from super.core.utils import get_app_conf as _get_app_conf_core
from super.core.utils import get_project_conf as _get_project_conf_core

DEFAULT_APP = "generate_powers"

# Define the configuration root relative to this file.
# Path: src/super/config.py
# Root structure:
# super-services/
#   conf/
#   src/
#     super/
#       config.py
SERVICE_CONF_ROOT = Path(__file__).resolve().parents[2] / "conf"


def get_app_conf(app: str = DEFAULT_APP, **kwargs) -> Any:
    """Load the app configuration for this package, using its own config root."""
    kwargs.setdefault("conf_root", SERVICE_CONF_ROOT)
    return _get_app_conf_core(app=app, **kwargs)


def get_project_conf(**kwargs) -> Any:
    """Load the project configuration for this package, using its own config root."""
    kwargs.setdefault("conf_root", SERVICE_CONF_ROOT)
    return _get_project_conf_core(**kwargs)
