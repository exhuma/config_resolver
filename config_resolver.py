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

__version__ = '3.0'

LOG = logging.getLogger(__name__)


class Config(object, SafeConfigParser):
    """
    :param search_path: if specified, set the config search path to the
        given value. The path can use OS specific separators (f.ex.: ``:``
        on posix, ``;`` on windows) to specify multiple folders. These
        folders will be searched in the specified order. The config files
        will be loaded incrementally. This means that the each subsequent
        config file will extend/override existing values. This means that
        the last file will take precedence.
    :param file_name: if specified, this can be used to override the
        configuration filename (default=``"app.ini"``)
    :param group_name: an application group (f. ex.: your company name)
    :param app_name: an application identifier (f.ex.: the application
                     module name)

    Environment Variables
    ---------------------

    The resolver can also be manipulated using environment variables to
    allow different values for different running instances:

    <app_name>_PATH
        The search path of config files. ``<app_name>`` is the application
        name in all caps. See the documentation for the ``search_path``
        parameter for an explanation of precedence.

    <app_name>_CONFIG
        The file name of the config file (default=``"app.ini"``)
    """

    def __init__(self, group_name, app_name, search_path=None,
            file_name='app.ini', **kwargs):
        SafeConfigParser.__init__(self, **kwargs)
        self.config = None
        self.group_name = group_name
        self.app_name = app_name
        self.search_path = search_path
        self.file_name = file_name
        self.loaded = False
        self.load()

    def load(self, reload=False):
        """
        Searches for an appropriate config file. If found, loads the file into
        the current instance. This method can also be used to re-load a
        configuration. Note that you may want to set ``reload`` to ``True`` to
        clear the configuration before loading in that case.  Without doing
        that, values will remain available even if they have been removed from
        the config files.

        :param reload: if set to ``True``, the existing values are cleared
                       before reloading.
        """

        if reload:
            self.config = None

        # only load the config if necessary (or explicitly requested)
        if self.config:
            LOG.debug('Returning cached config instance. Use '
                    '``reload=True`` to avoid caching!')
            return self.config

        path_var = "%s_PATH" % self.app_name.upper()
        filename_var = "%s_CONFIG" % self.app_name.upper()

        # default search path
        path = ['/etc/%s/%s' % (self.group_name, self.app_name),
                expanduser('~/.%s/%s' % (self.group_name, self.app_name)),
                getcwd()]

        # If a path was passed directly to this method, override the path.
        if self.search_path:
            path = self.search_path.split(pathsep)

        # if an environment variable was specified, override the path again.
        # Environment variables take absolute precedence.
        env_path = getenv(path_var)
        if env_path:
            LOG.info('Configuration search path was overridden with {0} by an '
                     'environment vaiable.'.format(env_path))
            path = env_path.split(pathsep)

        # same logic for the configuration filename. First, check if we were
        # initialized with a filename...
        config_filename = None
        if self.file_name:
            config_filename = self.file_name

        # ... next, take the value from the environment
        env_filename = getenv(filename_var)
        if env_filename:
            LOG.info('Configuration filename was overridden with {0} by an '
                     'environment vaiable.'.format(env_filename))
            config_filename = env_filename

        # Next, use the resolved path to find the filenames. Keep track of
        # which files we loaded in order to inform the user.
        for dirname in path:
            conf_name = join(dirname, config_filename)
            if exists(conf_name):
                self.read(conf_name)
                LOG.info('%s config from %s' % (
                    self.loaded and 'Updating' or 'Loading initial',
                    conf_name))
                self.loaded = True
            else:
                LOG.debug('%s does not exist. Skipping...' % (conf_name, ))

        if not self.loaded:
            LOG.warning("No config file named %s found! Search path was %r" % (
                config_filename, path))
