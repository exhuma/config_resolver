"""
Layered TOML configuration for a CLI tool.
"""

import os
import sys
from pathlib import Path

from platformdirs import (
    site_config_dir,
    user_config_path,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

APP = "bird-feeder"
FILENAME = "config.toml"


def default_files():
    """Return files, lowest precedence first."""
    site = site_config_dir(APP, multipath=True)
    dirs = reversed(site.split(os.pathsep))
    files = [Path(d, FILENAME) for d in dirs]
    files.append(user_config_path(APP) / FILENAME)
    return files


def merge(base, override):
    """Merge dicts; *override* wins."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(
            result.get(key), dict
        ):
            value = merge(result[key], value)
        result[key] = value
    return result


def load_config(explicit=None):
    """Return the config and its source files."""
    explicit = explicit or os.environ.get(
        "BIRD_FEEDER_CONFIG"
    )
    files = [
        f for f in default_files() if f.is_file()
    ]
    if explicit:
        # Must exist: open() fails if it does not.
        files.append(Path(explicit))
    config = {}
    for path in files:
        with path.open("rb") as fp:
            config = merge(
                config, tomllib.load(fp)
            )
    return config, files
