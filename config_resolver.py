"""
A config resolver for python.

Usage::

    from config_resolver import Config
    conf = Config('mycompany', 'myapplication')

Crating the config object will not raise an error. Instead it will return a
valid, but empty :py:class:`.Config` instance. In order to determine whether
any config file was loaded, you can look into the ``loaded_files`` instance
variable. It contains a list of all the loaded files, in the order of loading.
If that list is empty, no config has been found.

Additionally, another instance variable named ``active_path`` represents the
search path after processing of environment variables and runtime parameters.
This may be useful to display user-errors, or debugging.

The resolver parses config files according to the default python
``ConfigParser`` (i.e. ``ini`` files).
"""

from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from os import getenv, pathsep, getcwd
from os.path import expanduser, exists, join
import logging
from warnings import warn

__version__ = '3.2.1'

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
    :param filename: if specified, this can be used to override the
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

        If the path is prefixed with ``+``, then the path is *appended* to the
        default search path. This is the recommended way to specify the path,
        as it will not short-circuit the existing lookup logic.

    <app_name>_CONFIG
        The file name of the config file (default=``"app.ini"``)
    """

    def __init__(self, group_name, app_name, search_path=None,
                 filename='app.ini', **kwargs):
        SafeConfigParser.__init__(self, **kwargs)
        self.config = None
        self.group_name = group_name
        self.app_name = app_name
        self.search_path = search_path
        self.filename = filename
        self.loaded_files = []
        self.active_path = []
        self.load()

    def _get_env_filename(self):
        old_filename_var = "%s_CONFIG" % self.app_name.upper()
        filename_var = "%s_%s_CONFIG" % (
            self.group_name.upper(),
            self.app_name.upper())
        env_filename = getenv(old_filename_var)
        if env_filename:
            warn(DeprecationWarning('No group prefixed in environment '
                                    'variable! This behaviour is deprecated. '
                                    'See the docs!'))
        else:
            env_filename = getenv(filename_var)
        return env_filename

    def _get_env_path(self):
        old_path_var = "%s_PATH" % self.app_name.upper()
        path_var = "%s_%s_PATH" % (
            self.group_name.upper(),
            self.app_name.upper())

        env_path = getenv(old_path_var)
        if env_path:
            warn(DeprecationWarning('No group prefixed in environment '
                                    'variable! This behaviour is deprecated. '
                                    'See the docs!'))
        else:
            env_path = getenv(path_var)
        return env_path

    def get(self, section, option, default=None):
        """
        Overrides :py:meth:`SafeConfigParser.get`.

        In addition to ``section`` and ``option``, this call takes an optional
        ``default`` value. This behaviour works in *addition* to the
        SafeConfigParser default mechanism. Note that a default value from
        SafeConfigParser takes precedence.

        The reason this additional functionality is added, is because the
        defaults of ``SafeConfigParser`` are not dependent on secions. If you
        specify a default for the option ``test``, then this value will be
        returned for both ``section1.test`` and for ``section2.test``. Using
        the default on the ``get`` call gives you finer control over this.

        Default hits are logged with level ``logging.DEBUG``.
        """
        try:
            value = SafeConfigParser.get(self, section, option)
            return value
        except (NoSectionError, NoOptionError) as exc:
            LOG.debug("{0}: Returning default value {1!r}".format(exc,
                                                                  default))
            return default

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
            return

        # default search path
        path = ['/etc/%s/%s' % (self.group_name, self.app_name),
                expanduser('~/.%s/%s' % (self.group_name, self.app_name)),
                getcwd()]

        # If a path was passed directly to this method, override the path.
        if self.search_path:
            path = self.search_path.split(pathsep)

        # if an environment variable was specified, override the path again.
        # Environment variables take absolute precedence.
        env_path = self._get_env_path()

        if env_path and env_path.startswith('+'):
            additional_paths = env_path[1:].split(pathsep)
            LOG.info('Search path extended with with {0} by an environment '
                     'vaiable.'.format(additional_paths))
            path.extend(additional_paths)
        elif env_path:
            LOG.info('Configuration search path was overridden with {0} by an '
                     'environment vaiable.'.format(env_path))
            path = env_path.split(pathsep)

        # same logic for the configuration filename. First, check if we were
        # initialized with a filename...
        config_filename = None
        if self.filename:
            config_filename = self.filename

        # ... next, take the value from the environment
        env_filename = self._get_env_filename()
        if env_filename:
            LOG.info('Configuration filename was overridden with {0} by an '
                     'environment vaiable.'.format(env_filename))
            config_filename = env_filename

        # Next, use the resolved path to find the filenames. Keep track of
        # which files we loaded in order to inform the user.
        self.active_path = [join(_, config_filename) for _ in path]
        for dirname in path:
            conf_name = join(dirname, config_filename)
            if exists(conf_name):
                self.read(conf_name)
                LOG.info('%s config from %s' % (
                    self.loaded_files and 'Updating' or 'Loading initial',
                    conf_name))
                self.loaded_files.append(conf_name)
            else:
                LOG.debug('%s does not exist. Skipping...' % (conf_name, ))

        if not self.loaded_files:
            LOG.warning("No config file named %s found! Search path was %r" % (
                config_filename, path))
