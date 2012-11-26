"""
A config resolver for python.

Usage::

    from config_resolver import config
    conf = config('mycompany', 'myapplication')

The resolver parses config files according to the default python
``ConfigParser`` (i.e. ``ini`` files).
"""

from ConfigParser import SafeConfigParser
from os import getenv, pathsep, getcwd
from os.path import expanduser, exists, join
import logging

__version__ = '2.0.1'

LOG = logging.getLogger(__name__)
CONF = SafeConfigParser()
CONFIG_LOADED = False


def config(group, app, search_path=None, conf_name=None, force_reload=False):
    """
    Searches for an appropriate config file. If found, return the parsed
    config instance.

    After this is called, the config instance will also be available as
    ``config_resolver.CONF`` as a shortcut.

    :param group: an application group (f. ex.: your company name)
    :param app: an application identifier (f.ex.: the application module name)
    :param search_path: if specified, set the config search path to the given
        value. The path can use OS specific separators (f.ex.: ``:`` on posix,
        ``;`` on windows) to specify multiple folders. These folders will be
        searched in the specified order. The config files will be loaded
        incrementally. This means that the each subsequent config file will
        extend/override existing values. This means that the last file will
        take precedence.
    :param conf_name: if specified, this can be used to override the
        configuration filename (default=``"app.ini"``)
    :param force_reload: if set to true, the config is reloaded, even if it
        was alrady loaded in the application. Default = ``False``

    Environment Variables
    ---------------------

    The resolver can also be manipulated using environment variables to allow
    different values for different running instances:

    <app>_PATH
        The search path of config files. ``<app>`` is the application name in
        all caps. See the documentation for the ``search_path`` parameter for
        an explanation of precedence.

    <app>_CONFIG
        The file name of the config file (default=``"app.ini"``)
    """
    global CONFIG_LOADED

    # only load the config if necessary (or explicitly requested)
    if CONFIG_LOADED and not force_reload:
        LOG.debug('Returning cached config instance. Use '
                '``force_reload=True`` to avoid caching!')
        return CONF

    path_var = "%s_PATH" % app.upper()
    filename_var = "%s_CONFIG" % app.upper()

    # default search path
    path = ['/etc/%s/%s' % (group, app),
            expanduser('~/.%s/%s' % (group, app)),
            getcwd(),]

    # if an environment variable was specified, override the default path
    env_path = getenv(path_var)
    if env_path:
        path = env_path.split(pathsep)

    # If a path was passed directly to this method, override the path again
    if search_path:
        path = search_path.split(pathsep)

    # same logic for the configuration filename. First, try the runtime
    # environment (with a default fallback):
    config_filename = getenv(filename_var, 'app.ini')

    # If a filename was passed directly, override the value
    if conf_name:
        config_filename = conf_name

    # Next, use the resolved path to find the filenames. Keep track of which
    # files we loaded in order to inform the user.
    CONFIG_LOADED = False
    for dirname in path:
        conf_name = join(dirname, config_filename)
        if exists(conf_name):
            CONF.read(conf_name)
            LOG.info('{0} config from {1}'.format(
                CONFIG_LOADED and 'Updating' or 'Loading initial',
                conf_name))
            CONFIG_LOADED = True
        else:
            LOG.debug('{0} does not exist. Skipping...'.format(conf_name))

    if not CONFIG_LOADED:
        LOG.warning("No config file named %s found! Search path was %r" % (
            config_filename, path))

    return CONF
