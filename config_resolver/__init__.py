'''
Main package for config_resolver. It provides a central point for imports, for
example::

    from config_resolver import get_config

It also provides metadata:

* ``config_resolver.__version__``
'''
# pylint: disable=unused-import

from os.path import dirname, join

from .core import (
    NoVersionError,
    from_string,
    get_config,
)


with open(join(dirname(__file__), 'version.txt')) as fptr:
    __version__ = fptr.read().strip()
