"""
Helpers and utilities for the config_resolver package.

This module contains stuff which is not directly impacting the business logic of
the config_resolver package.
"""
from logging import Filter, LogRecord
from typing import Any


class PrefixFilter(Filter):
    """
    A logging filter which prefixes each message with a given text.

    :param prefix: The log prefix.
    :param separator: A string to put between the prefix and the original log
                      message.
    """

    # pylint: disable = too-few-public-methods

    def __init__(self, prefix: str, separator: str = " ") -> None:
        super().__init__()
        self._prefix = prefix
        self._separator = separator

    def __eq__(self, other: Any) -> bool:
        # NOTE: using ``isinstance(other, PrefixFilter)`` did NOT work properly
        # when running the unit-tests through ``sniffer``. Does this have
        # something to do with ``sniffer`` or is there something wrong with the
        # code of ``config_resolver``? This is a workaround which is incorrect,
        # and could in extreme cases cause problems if there was another
        # filter with the exact same class name and with a ``_prefix`` and
        # ``_separator`` member. They would wrongly be assumed to be the same.
        # I'll assume this won't happen for now.
        # pylint: disable = protected-access
        return (
            self.__class__.__name__ == other.__class__.__name__
            and other._prefix == self._prefix  # type: ignore
            and other._separator == self._separator
        )

    def __repr__(self) -> str:
        return "PrefixFilter(prefix={!r}, separator={!r}>".format(
            self._prefix, self._separator
        )

    def filter(self, record: LogRecord) -> bool:
        # pylint: disable = missing-docstring
        record.msg = self._separator.join([self._prefix, record.msg])
        return True
