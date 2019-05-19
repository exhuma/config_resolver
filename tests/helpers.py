"""
Helpers for unit-tests
"""

from contextlib import contextmanager
import os
import logging
import re

__unittest = True  # Magic value to hide stack-traces in unit-test output


def execute(filename):
    '''
    Execute the python module in *filename* and return the resulting globals.
    '''
    with open(filename) as fptr:
        source = fptr.read()
    ast = compile(source, filename, 'exec')
    globals_ = {}
    exec(ast, globals_)
    return globals_


@contextmanager
def environment(**kwargs):
    """
    Context manager to tempolrarily change environment variables. On exit all
    variables are set to their original value.
    """
    old_values = {}
    nonexistent = set()
    for key in kwargs:
        if key not in os.environ:
            nonexistent.add(key)
        else:
            old_values[key] = os.environ[key]
        os.environ[key] = kwargs[key]
    try:
        yield
    finally:
        for key in old_values:
            os.environ[key] = old_values[key]
        for key in nonexistent:
            os.environ.pop(key)


class TestableHandler(logging.Handler):
    """
    A logging handler which is usable in unit tests. Log records are simply
    appended to an internal list and can be checked with ``contains``.
    """

    def __init__(self, *args, **kwargs):
        super(TestableHandler, self).__init__(*args, **kwargs)
        self.records = []

    def emit(self, record):
        """
        Overrides :py:meth:`logging.Handler.emit`.
        """
        self.records.append(record)

    def assert_contains(self, logger, level, needle):
        if not self.contains(logger, level, needle):
            msg = '%s did not contain a message with %r and level %r'
            raise AssertionError(msg % (logger, needle, level))

    def assert_contains_regex(self, logger, level, needle):
        if not self.contains(logger, level, needle, is_regex=True):
            msg = '%s did not contain a message matching %r and level %r'
            raise AssertionError(msg % (logger, needle, level))

    def contains(self, logger, level, message, is_regex=False):
        """
        Checks whether a message has been logged to a specific logger with a
        specific level.

        :param logger: The logger.
        :param level: The log level.
        :param messgae: The message contents.
        :param is_regex: Whether the expected message is a regex or not.
            Non-regex messages are simply tested for inclusion.
        """
        for record in self.records:
            if record.name != logger or record.levelno != level:
                continue
            if is_regex:
                if re.search(message, (record.msg % record.args)):
                    return True
            else:
                if message in (record.msg % record.args):
                    return True
        return False

    def reset(self):
        del self.records[:]



