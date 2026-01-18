"""Configuration helpers for Super Services."""


import os
from pathlib import Path
from typing import Any, Final
from typing import cast

from pyhocon import ConfigFactory, ConfigTree

DEFAULT_APP: Final[str | None] = None
TypedConfig = Any


def _parse_hocon(path: Path) -> ConfigTree:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"HOCON config not found at {resolved}")
    conf = ConfigFactory.parse_file(resolved.as_posix(), resolve=False)
    return cast(TypedConfig, conf)




def _resolve_conf_root() -> Path:
    """Resolve the configuration root directory.
    
    Defaults to looking for 'conf' in the current working directory.
    Callers should prefer passing an explicit 'conf_root' argument.
    """
    cwd = Path.cwd()
    
    # Require an explicit conf directory; no silent fallback.
    conf_root = cwd / "conf"
    if conf_root.exists():
        return conf_root

    raise FileNotFoundError(f"Configuration root not found at {conf_root}")


def get_project_conf(
    *,
    resolve: bool = True,
    conf_root: Path | None = None,
) -> TypedConfig:
    """Load the shared project configuration.

    Args:
        include_developer: When True (default) merge `conf/developer/developer.conf`
            on top of the base project configuration if it exists.
        conf_root: Exact path to the configuration root directory.
    """
    
    if conf_root is None:
        conf_root = _resolve_conf_root()
    
    # If we found conf_root, we assume project_root is its grandparent (repo root)
    # e.g. conf_root=.../services/conf -> parent=.../services -> parent.parent=.../repo
    project_root = conf_root.parent.parent

    project_name = project_root.name
    
    # Determine and create staging root
    home = Path.home()
    stage_root = home / "stage" / project_name
    try:
        stage_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback to tmp if we can't create in home (though unlikely for user)
        pass

    runtime_defaults = ConfigFactory.from_dict(
        {
            "project_root": project_root.as_posix(),
            "stage_root": stage_root.as_posix(),
        }
    )

    project_conf = _parse_hocon(conf_root / "project.conf").with_fallback(runtime_defaults)

    # Order of overlays: secrets -> developer secrets -> developer config
    overlays = [
        "secret.conf", # Project secrets
        "developer/secrets.conf", # Developer overrides for secrets
        "developer/developer.conf", # Developer local overrides
    ]

    for overlay in overlays:
        overlay_path = (conf_root / overlay).resolve()
        if overlay_path.exists():
            project_conf = _parse_hocon(overlay_path).with_fallback(project_conf)

    if resolve:
        project_conf = project_conf.resolve(project_conf)

    return project_conf


def get_app_conf(
    app: str | None = DEFAULT_APP,
    app_conf_root: Path | None = None,
    conf_root: Path | None = None,
) -> TypedConfig:
    """Load the app configuration merged with the project defaults.
    
    Args:
        app: Name of the application (e.g. "sage"). If None, loads only project config.
        app_conf_root: Explicit path to the app configuration directory (legacy argument).
        conf_root: Path to the main configuration root (containing project.conf and apps/).
    """

    # Pass the context to project config loader
    project_conf = get_project_conf(resolve=False, conf_root=conf_root)

    if app is None:
        # If no app specified, return strictly project config (no app layer).
        return project_conf.resolve(project_conf)

    if app_conf_root is not None:
        app_conf_path = Path(app_conf_root).resolve()
    else:
        if conf_root is None:
            conf_root = _resolve_conf_root()
            
        apps_root = Path(conf_root / "apps").resolve()

        app_conf_path = Path(apps_root / app / "app.conf").resolve()

    app_conf = _parse_hocon(app_conf_path)
    app_conf.put("app", app)
    app_conf.put("app_conf_root", app_conf_path.as_posix())

    merged = app_conf.with_fallback(project_conf)

    # Developer overlays for apps as well
    overlays = [
        "developer/secrets.conf",
        "developer/developer.conf",
    ]

    for overlay in overlays:
        overlay_path = (conf_root / overlay).resolve()
        if overlay_path.exists():
            merged = _parse_hocon(overlay_path).with_fallback(merged)

    return merged.resolve(merged)

    return merged.resolve(merged)
__all__ = ["DEFAULT_APP", "get_app_conf", "get_project_conf"]
