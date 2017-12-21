from os.path import dirname, join

from .core import (
    Config,
    NoVersionError,
    SecuredConfig,
    from_string,
    get_config,
)


with open(join(dirname(__file__), 'version.txt')) as fptr:
    __version__ = fptr.read().strip()
