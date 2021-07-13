"""
This module contains helpers for type hinting
"""

from typing import Any, Generic, Optional, TypeVar

from packaging.version import Version

TConfig = TypeVar("TConfig", bound=Any)  # pylint: disable=invalid-name


class Handler(Generic[TConfig]):
    """
    A generic config file handler. Concrete classes should be created in order
    to support new file formats.
    """

    #: The filename that is used when the user did not specify a filename when
    #: retrieving the config instance
    DEFAULT_FILENAME = "unknown"

    @staticmethod
    def empty() -> TConfig:
        """
        Create an empty configuration instance.
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def from_string(data: str) -> TConfig:
        """
        Create a configuration instance from a text-string
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def from_filename(filename: str) -> TConfig:
        """
        Create a configuration instance from a file-name.
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def get_version(config: TConfig) -> Optional[Version]:
        """
        Retrieve the parsed version number from a given config instance.
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def update_from_file(config: TConfig, filename: str) -> None:
        """
        Updates an existing config instance from a given filename.

        The config instance in *data* will be modified in-place!
        """
        raise NotImplementedError("Not yet implemented")
