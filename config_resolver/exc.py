class IncompatibleVersion(Exception):
    """
    This exception is raised if a config file is loaded which has a different
    major version number than expected by the application.
    """


class NoVersionError(Exception):
    """
    This exception is raised if the application expects a version number to be
    present in the config file but does not find one.
    """
