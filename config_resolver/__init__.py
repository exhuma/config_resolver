"""
The ``config_resolver`` package provides an easy way to create an instance of
a config object.

The main interface of this package is
:py:func:`config_resolver.core.get_config` (also provided via
``config_resolver.get_config``).

This function takes a fair amount of options to control how config files are
loaded. The easiest example is::

    >>> from config_resolver import get_config
    >>> config, metadata = get_config("myapp")

This call will scan through a number of folders and load/update the config
with every matching file in that chain. Some customisation of that load
process is made available via the :py:func:`~config_resolver.core.get_config`
arguments.

The call retuns a config instance, and some meta-data related to the loading
process. See :py:func:`~config_resolver.core.get_config` for details.

``config_resolver`` comes with support for ``.json`` and ``.ini`` files out
of the box. It is possible to create your own handlers for other file types
by subclassing :py:class:`config_resolver.handler.Handler` and passing it to
:py:func:`~config_resolver.core.get_config`
"""
# pylint: disable=unused-import

from os.path import dirname, join

from .core import from_string, get_config
from .exc import NoVersionError

with open(join(dirname(__file__), "version.txt")) as fptr:
    __version__ = fptr.read().strip()
