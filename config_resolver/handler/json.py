"""
Handler for JSON files
"""

from json import load, loads
from typing import Any, Dict, Optional

from packaging.version import Version

from .base import Handler

TJsonConfig = Dict[str, Any]


class JsonHandler(Handler[TJsonConfig]):
    """
    A config-resolver handler capable of reading ".json" files.
    """

    DEFAULT_FILENAME = "app.json"

    @staticmethod
    def empty() -> TJsonConfig:
        return {}

    @staticmethod
    def from_string(data: str) -> TJsonConfig:
        return loads(data)  # type: ignore

    @staticmethod
    def from_filename(filename: str) -> TJsonConfig:
        with open(filename) as fptr:
            output = load(fptr)
        return output  # type: ignore

    @staticmethod
    def get_version(config: TJsonConfig) -> Optional[Version]:
        if "meta" not in config or "version" not in config["meta"]:
            return None
        raw_value = config["meta"]["version"]
        parsed = Version(raw_value)
        return parsed

    @staticmethod
    def update_from_file(config: TJsonConfig, filename: str) -> None:
        with open(filename) as fptr:
            new_data = load(fptr)
            config.update(new_data)
