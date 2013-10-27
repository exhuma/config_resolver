try:
    from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
except ImportError:
    from configparser import SafeConfigParser, NoOptionError, NoSectionError

from os import getenv, pathsep, getcwd, stat as get_stat
from os.path import expanduser, exists, join
import logging
import stat
from warnings import warn
from distutils.version import StrictVersion

__version__ = '4.0.0'

LOG = logging.getLogger(__name__)


class IncompatibleVersion(Exception):
    pass


class NoVersionError(Exception):
    pass


try:
    # Python 2
    class ConfigResolverBase(object, SafeConfigParser):
        pass
except TypeError:
    # Python 3
    class ConfigResolverBase(SafeConfigParser):
        pass


class Config(ConfigResolverBase):
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
        instance will raise an :py:exc:`OSError` if not a single file could be
        loaded.
    :param version: If specified (f.ex.: ``version='2.0'``), this will create a
        versioned config instance. A versioned instance may raise a
        :py:exc:`.IncompatibleVersion` exception if the major version differs
        from the one found in the config file. If left to the default, no
        version checking is performed.
    """

    def __init__(self, group_name, app_name, search_path=None,
                 filename='app.ini', require_load=False, version=None,
                 **kwargs):
        SafeConfigParser.__init__(self, **kwargs)
        self.version = version and StrictVersion(version) or None
        self.config = None
        self.group_name = group_name
        self.app_name = app_name
        self.search_path = search_path
        self.filename = filename
        self.loaded_files = []
        self.active_path = []
        self.load(require_load=require_load)

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
        env_filename = getenv(self.env_filename_name)
        if env_filename:
            LOG.info('Configuration filename was overridden with {0!r} by the '
                     'environment variable HELLO_WORLD_FILENAME.'.format(
                         env_filename))
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
                join(getcwd(), '.{}'.format(self.group_name), self.app_name)]

        # If a path was passed directly to this instance, override the path.
        if self.search_path:
            path = self.search_path.split(pathsep)

        # Next, consider the environment variables...
        env_path = getenv(self.env_path_name)

        if env_path and env_path.startswith('+'):
            # If prefixed with a '+', append the path elements
            additional_paths = env_path[1:].split(pathsep)
            LOG.info('Search path extended with {0!r} by the environment '
                     'variable HELLO_WORLD_PATH.'.format(additional_paths))
            path.extend(additional_paths)
        elif env_path:
            # Otherwise, override again. This takes absolute precedence.
            LOG.info("Configuration search path was overridden with {0!r} by "
                     "the environment variable {1!r}.".format(
                         env_path,
                         self.env_path_name))
            path = env_path.split(pathsep)

        return path

    @property
    def env_filename_name(self):
        return "%s_%s_FILENAME" % (
            self.group_name.upper(),
            self.app_name.upper())

    @property
    def env_path_name(self):
        return "%s_%s_PATH" % (
            self.group_name.upper(),
            self.app_name.upper())

    def check_file(self, filename):
        """
        Check if ``filename`` can be read. Will return a 2-tuple containing a
        boolean if the file can be read, and a string containing the cause
        (empty if the file is readable).

        This mainly exists to make it possible to override this with different
        rules.
        """
        if exists(filename):
            return True, ''
        else:
            return False, 'File does not exist'

    def get(self, section, option, **kwargs):
        """
        Overrides :py:meth:`configparser.SafeConfigParser.get`.

        In addition to ``section`` and ``option``, this call takes an optional
        ``default`` value. This behaviour works in *addition* to the
        :py:class:`configparser.SafeConfigParser` default mechanism. Note that
        a default value from ``SafeConfigParser`` takes precedence.

        The reason this additional functionality is added, is because the
        defaults of :py:class:`configparser.SafeConfigParser` are not dependent
        on sections. If you specify a default for the option ``test``, then
        this value will be returned for both ``section1.test`` and for
        ``section2.test``. Using the default on the ``get`` call gives you more
        fine-grained control over this.

        Also note, that if a default value has to be used, it will be logged
        with level ``logging.DEBUG``.

        :param section: The config file section.
        :param option: The option name.
        """
        try:
            value = SafeConfigParser.get(self, section, option)
            return value
        except (NoSectionError, NoOptionError) as exc:
            if "default" in kwargs:
                LOG.debug("{0}: Returning default value {1!r}".format(
                    exc,
                    kwargs['default']))
                return kwargs['default']
            else:
                raise

    def load(self, reload=False, require_load=False):
        """
        Searches for an appropriate config file. If found, loads the file into
        the current instance. This method can also be used to reload a
        configuration. Note that you may want to set ``reload`` to ``True`` to
        clear the configuration before loading in that case.  Without doing
        that, values will remain available even if they have been removed from
        the config files.

        :param reload: if set to ``True``, the existing values are cleared
                       before reloading.
        :param require_load: If set to ``True`` this will raise a
                             :py:exc:`IOError` if no config file has been found
                             to load.
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
                LOG.warning('Unable to read %r (%s)' % (conf_name, cause))

        if not self.loaded_files and not require_load:
            LOG.warning("No config file named %s found! Search path was %r" % (
                config_filename, path))
        elif not self.loaded_files and require_load:
            raise IOError("No config file named %s found! Search path "
                          "was %r" % (config_filename, path))

    def read(self, *args, **kwargs):
        """
        Overrides :py:meth:`configparser.SafeConfigParser.read`.

        In addition to the default ``read`` method, this does version checking
        if this instance has been created with a version number. It uses
        :py:class:`distutils.version.StrictVersion` for version parsing.
        """
        output = super(Config, self).read(*args, **kwargs)
        if not self.version:
            # No versioning is expected, so we can ignore the rest of this
            # method.
            return output

        # The config object was apparently instantiated with a version number.
        # Check that config files we read have appropriate version information.
        if self.has_option('meta', 'version'):
            major, minor, _ = StrictVersion(
                self.get('meta', 'version')).version
            expected_major, expected_minor, _ = self.version.version

            if expected_major != major:
                raise IncompatibleVersion(
                    'Invalid major version number. Expected {!r}, got {!r} '
                    'from filename {!r}!'.format(expected_major, major,
                                                 args[0]))

            if expected_minor != minor:
                LOG.warning('Mismatching minor version number. '
                            'Expected {!r}, got {!r} '
                            'from filename {!r}'.format(expected_minor, minor,
                                                        args[0]))
        else:
            raise NoVersionError(
                "The config option 'meta.version' is missing in {}. The "
                "application expects version {}!".format(args[0],
                                                         self.version))


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
