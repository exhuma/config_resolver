"""
This module contains helpers for type hinting
"""

from typing import Any, Generic, TypeVar

from config_resolver.dirty import StrictVersion  # type: ignore

T = TypeVar("T", bound=Any)  # pylint: disable=invalid-name


class Handler(Generic[T]):
    """
    A generic config file handler. Concrete classes should be created in order
    to support new file formats.
    """

    @staticmethod
    def empty() -> T:
        """
        Create an empty configuration instance.
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def from_string(data: str) -> T:
        """
        Create a configuration instance from a text-string
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def from_filename(filename: str) -> T:
        """
        Create a configuration instance from a file-name.
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def get_version(config: T) -> StrictVersion:
        """
        Retrieve the parsed version number from a given config instance.
        """
        raise NotImplementedError("Not yet implemented")

    @staticmethod
    def update_from_file(config: T, filename: str) -> None:
        """
        Updates an existing config instance from a given filename.

        The config instance in *data* will be modified in-place!
        """
        raise NotImplementedError("Not yet implemented")
