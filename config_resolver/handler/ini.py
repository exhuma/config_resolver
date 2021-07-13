"""
Handler for INI files
"""

from configparser import ConfigParser
from typing import Optional

from packaging.version import Version

from .base import Handler


class IniHandler(Handler[ConfigParser]):
    """
    A config-resolver handler capable of reading ".ini" files.
    """

    DEFAULT_FILENAME = "app.ini"

    @staticmethod
    def empty() -> ConfigParser:
        return ConfigParser()

    @staticmethod
    def from_string(data: str) -> ConfigParser:
        parser = ConfigParser()
        parser.read_string(data)
        return parser

    @staticmethod
    def from_filename(filename: str) -> ConfigParser:
        parser = ConfigParser()
        with open(filename) as fptr:
            parser.read_file(fptr)
        return parser

    @staticmethod
    def get_version(config: ConfigParser) -> Optional[Version]:
        if not config.has_section("meta") or not config.has_option(
            "meta", "version"
        ):
            return None
        raw_value = config.get("meta", "version")
        parsed = Version(raw_value)
        return parsed

    @staticmethod
    def update_from_file(config: ConfigParser, filename: str) -> None:
        with open(filename) as fptr:
            config.read_file(fptr)
