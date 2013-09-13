"""
`config_resolver` is a module which searches for config files using a
predictable pattern, while still making it posible for the end-user to override
this search (that is, the end-user can always specify his/her own config file).

Config files are parsed using the default python ``ConfigParser`` (i.e. ``ini``
files).

The module assumes a fairly common pattern to have both an application "group"
(for example the company name) and an application name and will search in
appropriate locations. For example, if your company is named "acme_corp" and
you had an application named "bird_feeder" it would search in the following
folders:

* ``/etc/acmecorp/bird_feeder/app.ini``
* ``~/.acmecorp/bird_feeder/app.ini``
* ``./app.ini``

Both the search path and the basename of the file (`app.ini`) can be overridden
by the application developer via the API and by the end-user via environment
variables.

.. note::
    Both the ``filename`` API argument, and the ``GROUP_APP_CONFIG``
    environment variable override the config file *basename*. Not the folder!

File loading proceeds in the same order as displayed above, and each new read
will override values from a previous file. This means that the file in
`~/.acmecorp/bird_feeder` will override the values from the file in
`/etc/acmecorp/bird_feeder`. And lastly, if a file named `app.ini` is found in
the *current working folder*, that file will again override already loaded
values. This can come in very handy when running multiple instances of the same
application, but want to run each instance with a different config.

Basic Usage
-----------

In it's most basic form, the following two lines are all you need::

    from config_resolver import Config
    conf = Config('mycompany', 'myapplication')

Note that when using `config_resolver` in this way, non-existing files will be
silently ignored (logged).

All operations are logged using the default ``logging`` package. The log
messages include the absolute names of the loaded files. If a file is not
loadable, a ``WARNING`` message is emitted. It also contains a couple of
``DEBUG`` messages. If you want to see those messages on-screen you could do
the following (not suitable for production code!)::

    import logging
    from config_resolver import Config
    logging.basicConfig(level=logging.DEBUG)
    conf = Config('mycompany', 'myapplication')

Environment Variables
---------------------

The resolver can also be manipulated using environment variables to allow
different values for different running instances. The variable names are all
upper-case and are prefixed with both group- and application-name.

<group_name>_<app_name>_PATH
    The search path for config files. You can specify multiple paths by
    separating it by the system's path separator default (``:`` on *nix).

    If the path is prefixed with ``+``, then the path elements are *appended*
    to the default search path. This is the recommended way to specify the
    path, as it will not short-circuit the existing lookup logic.

<group_name>_<app_name>_CONFIG
    The file name of the config file. Note that this should *not* be given with
    leading path elements. It should simply be a file basename (f.ex.:
    ``my_config.ini``)

Difference to ConfigParser
~~~~~~~~~~~~~~~~~~~~~~~~~~

There is one **major** difference to the default Python ``ConfigParser``: the
``.get`` method accepts a "default" parameter which itself defaults to
``None``.  This in turn means that the errors `NoSectionError` and
`NoOptionError` are **not** raised as you might expect. Instead, the default
value is returned in such a case. This is **intentional**! I find the support
for default values in the core library's ``ConfigParser`` lacking, you cannot
have two options with the same name in two sections with *different* values.
Imagine the following::

    [database1]
    dsn=sqlite:///tmp/db.sqlite3

    [database2]
    dsn=sqlite:///tmp/db2.sqlite3

In the core ``ConfigParser`` you could *not* specify two different default
values!

It turned out however, that sometimes people want those errors to be raised.
For that reason, a new ``mandatory`` argument has been added to the ``.get``
method. If that is set to ``True`` (defaults to ``False``), then the
appropriate errors are raised again.

Advanced Usage
--------------

Since version 3.3.0, you have a bit more control about how files are loaded.
:py:class:`.Config` has a new paramter: ``require_load``. If this is set to
``True``, an ``OSError`` is raised if no config file was loaded. Alternatively,
and, purely a matter of taste, you can leave this on it's default ``False``
value and inspect the ``loaded_files`` attribute on the ``Config`` instance. If
it's empty, nothing has been loaded.

Additionally, you can use :py:class:`.SecuredConfig`. This class refuses to
load config files which are readable by other users than the owner.

Debugging
---------

Creating the config object will not raise an error (except if asked to do so).
Instead it will always return a valid, (but possibly empty) :py:class:`.Config`
instance. So errors can be hard to see sometimes.

Your first stop should be to configure logging and look at the emitted
messages. If that does not help, then continue reading.

In order to determine whether any config file was loaded, you can look into the
``loaded_files`` instance variable. It contains a list of all the loaded files,
in the order of loading.  If that list is empty, no config has been found. Also
remember that the order is important. Later elements will override values from
earliner elements.

Additionally, another instance variable named ``active_path`` represents the
search path after processing of environment variables and runtime parameters.
This may also be useful to display informtation to the end-user.
"""

from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
from os import getenv, pathsep, getcwd, stat as get_stat
from os.path import expanduser, exists, join
import logging
import stat
from warnings import warn

__version__ = '3.3.0'

LOG = logging.getLogger(__name__)


class Config(object, SafeConfigParser):
    """
    :param group_name: an application group (f. ex.: your company name)
    :param app_name: an application identifier (f.ex.: the application
                     module name)
    :param search_path: if specified, set the config search path to the
        given value. The path can use OS specific separators (f.ex.: ``:``
        on posix, ``;`` on windows) to specify multiple folders. These
        folders will be searched in the specified order. The config files
        will be loaded incrementally. This means that the each subsequent
        config file will extend/override existing values. This means that
        the last file will take precedence.
    :param filename: if specified, this can be used to override the
        configuration filename.
    :param require_load: If this is set to ``True``, creation of the config
        instance will raise an ``OSError`` if not a single file could be
        loaded.
    """

    def __init__(self, group_name, app_name, search_path=None,
                 filename='app.ini', require_load=False, **kwargs):
        SafeConfigParser.__init__(self, **kwargs)
        self.config = None
        self.group_name = group_name
        self.app_name = app_name
        self.search_path = search_path
        self.filename = filename
        self.loaded_files = []
        self.active_path = []
        self.load(require_load=require_load)

    def _get_env_filename(self):
        """
        Returns the config filename from the environment variable if it exists.
        Otherwise it will return None.

        The environment variable must be named <GROUP_NAME>_<APP_NAME>_CONFIG
        """
        old_filename_var = "%s_CONFIG" % self.app_name.upper()
        filename_var = "%s_%s_CONFIG" % (
            self.group_name.upper(),
            self.app_name.upper())
        env_filename = getenv(old_filename_var)
        if env_filename:  # pragma: no cover
            warn(DeprecationWarning('No group prefixed in environment '
                                    'variable! This behaviour is deprecated. '
                                    'See the docs!'))
        else:
            env_filename = getenv(filename_var)
        return env_filename

    def _get_env_path(self):
        """
        Returns the search path from the environment variable. None if it does
        not exist.

        The environment variable must be named <GROUP_NAME>_<APP_NAME>_PATH
        """
        old_path_var = "%s_PATH" % self.app_name.upper()
        path_var = "%s_%s_PATH" % (
            self.group_name.upper(),
            self.app_name.upper())

        env_path = getenv(old_path_var)
        if env_path:  # pragma: no cover
            warn(DeprecationWarning('No group prefixed in environment '
                                    'variable! This behaviour is deprecated. '
                                    'See the docs!'))
        else:
            env_path = getenv(path_var)
        return env_path

    def _effective_filename(self):
        """
        Returns the filename which is effectively used by the application. If
        overridden by an environment variable, it will return that filename.
        """
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

        return config_filename

    def _effective_path(self):
        """
        Returns a list of paths to search for config files in reverse order of
        precedence.  In other words: the last path element will override the
        settings from the first one.
        """
        # default search path
        path = ['/etc/%s/%s' % (self.group_name, self.app_name),
                expanduser('~/.%s/%s' % (self.group_name, self.app_name)),
                getcwd()]

        # If a path was passed directly to this instance, override the path.
        if self.search_path:
            path = self.search_path.split(pathsep)

        # Next, consider the environment variables...
        env_path = self._get_env_path()

        if env_path and env_path.startswith('+'):
            # If prefixed with a '+', append the path elements
            additional_paths = env_path[1:].split(pathsep)
            LOG.info('Search path extended with with {0} by an environment '
                     'vaiable.'.format(additional_paths))
            path.extend(additional_paths)
        elif env_path:
            # Otherwise, override again. This takes absolute precedence.
            LOG.info('Configuration search path was overridden with {0} by an '
                     'environment variable.'.format(env_path))
            path = env_path.split(pathsep)

        return path

    def check_file(self, filename):
        """
        Check if a file can be read. Will return a 2-tuple containing a boolean
        if the file can be read, and a string containing the cause (empty if
        the file is readable).

        This mainly exists to make it possible to override this with different
        rules.
        """
        if exists(filename):
            return True, ''
        else:
            return False, 'File does not exist'

    def get(self, section, option, default=None, mandatory=False):
        """
        Overrides :py:meth:`SafeConfigParser.get`.

        In addition to ``section`` and ``option``, this call takes an optional
        ``default`` value. This behaviour works in *addition* to the
        ``SafeConfigParser`` default mechanism. Note that a default value from
        ``SafeConfigParser`` takes precedence.

        The reason this additional functionality is added, is because the
        defaults of ``SafeConfigParser`` are not dependent on sections. If you
        specify a default for the option ``test``, then this value will be
        returned for both ``section1.test`` and for ``section2.test``. Using
        the default on the ``get`` call gives you more fine-grained control
        over this.

        Also note, that if a default value has to be used, it will be logged
        with level ``logging.DEBUG``.

        If the optional argument ``mandatory`` is set to ``True``, this method
        will *always* raise a :py:exc:`ConfigParser.NoOptionError` or a
        :py:exc:`NoSectionError`, even if defaults have been passed in
        following the ``SafeConfigParser`` semantics.
        """
        if mandatory and not self.has_section(section):
            raise NoSectionError(section)
        elif mandatory and not self.has_option(section, option):
            raise NoOptionError(option, section)

        try:
            value = SafeConfigParser.get(self, section, option)
            return value
        except (NoSectionError, NoOptionError) as exc:
            LOG.debug("{0}: Returning default value {1!r}".format(exc,
                                                                  default))
            return default

    def load(self, reload=False, require_load=False):
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

        if reload:  # pragma: no cover
            self.config = None

        # only load the config if necessary (or explicitly requested)
        if self.config:  # pragma: no cover
            LOG.debug('Returning cached config instance. Use '
                      '``reload=True`` to avoid caching!')
            return

        path = self._effective_path()
        config_filename = self._effective_filename()

        # Next, use the resolved path to find the filenames. Keep track of
        # which files we loaded in order to inform the user.
        self.active_path = [join(_, config_filename) for _ in path]
        for dirname in path:
            conf_name = join(dirname, config_filename)
            readable, cause = self.check_file(conf_name)
            if readable:
                self.read(conf_name)
                LOG.info('%s config from %s' % (
                    self.loaded_files and 'Updating' or 'Loading initial',
                    conf_name))
                self.loaded_files.append(conf_name)
            else:
                LOG.debug('Unable to read %s (%s)' % (conf_name, cause))

        if not self.loaded_files and not require_load:
            LOG.warning("No config file named %s found! Search path was %r" % (
                config_filename, path))
        elif not self.loaded_files and require_load:
            raise IOError("No config file named %s found! Search path "
                          "was %r" % (config_filename, path))


class SecuredConfig(Config):
    """
    A subclass of :py:class:`.Config` which will refuse to load config files
    which are read able by other users than the owner.
    """

    def check_file(self, filename):
        """
        Overrides :py:meth:`.Config.check_file`
        """
        can_read, reason = super(SecuredConfig, self).check_file(filename)
        if not can_read:
            return False, reason

        mode = get_stat(filename).st_mode
        if (mode & stat.S_IRGRP) or (mode & stat.S_IROTH):
            return False, "File is not secure enough. Change it's mode to 600"
        else:
            return True, ''
