"""
Read the INI files config_resolver used to read.
"""

import os
from configparser import ConfigParser
from pathlib import Path


def config_paths(group, app, filename="app.ini"):
    home = os.environ.get(
        "XDG_CONFIG_HOME", Path.home() / ".config"
    )
    xdg_dirs = os.environ.get(
        "XDG_CONFIG_DIRS", "/etc/xdg"
    ).split(":")
    # Lowest precedence first.
    return [
        Path("/etc", group, app, filename),
        *(
            Path(d, group, app, filename)
            for d in reversed(xdg_dirs)
        ),
        Path(home, group, app, filename),
        Path.cwd() / f".{group}" / app / filename,
    ]


def load_config(group, app):
    config = ConfigParser()
    # read() skips missing files, applies the rest
    # in order and returns the ones it loaded.
    loaded_files = config.read(
        config_paths(group, app)
    )
    if not loaded_files:
        raise FileNotFoundError(
            "no config file found"
        )
    return config, loaded_files
