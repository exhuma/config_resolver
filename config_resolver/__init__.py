from os.path import dirname, join

from .core import Config, SecuredConfig, NoVersionError  # NOQA


with open(join(dirname(__file__), 'version.txt')) as fptr:
    __version__ = fptr.read().strip()
