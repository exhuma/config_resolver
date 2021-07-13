"""
Exceptions for the config_resolver package
"""


class NoVersionError(Exception):
    """
    This exception is raised if the application expects a version number to be
    present in the config file but does not find one.
    """

    pass
