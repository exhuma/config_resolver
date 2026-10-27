"""
Exceptions for the config_resolver package
"""


class NoVersionError(Exception):
    """
    This exception is raised if the application expects a version number to be
    present in the config file but does not find one.
    """

    pass


class ConfigResolverDeprecationWarning(DeprecationWarning):
    """
    Emitted on every call to :py:func:`~config_resolver.core.get_config` and
    :py:func:`~config_resolver.core.from_string`.

    ``config_resolver`` is no longer maintained. The warning points to the
    migration guide. Silence it with :py:func:`warnings.filterwarnings` while
    migrating away.
    """
