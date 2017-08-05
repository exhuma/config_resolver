"""
config_resolver provides a ``Config`` class, which looks up common locations
for config files and loads them if found. It provides a framework independed
way of handling configuration files. Additional care has been taken to allow
the end-user of the application to override this lookup process.
"""
try:
    from ConfigParser import SafeConfigParser, NoOptionError, NoSectionError
except ImportError:
    from configparser import ConfigParser, NoOptionError, NoSectionError

from os import getenv, pathsep, getcwd, stat as get_stat
from os.path import expanduser, exists, join
import logging
import stat
import sys
from distutils.version import StrictVersion

__version__ = '4.2.3'


class PrefixFilter(object):
    """
    A logging filter which prefixes each message with a given text.

    :param prefix: The log prefix.
    :param separator: A string to put between the prefix and the original log
                      message.
    """

    def __init__(self, prefix, separator=' '):
        self._prefix = prefix
        self._separator = separator

    def __eq__(self, other):
        # NOTE: using ``isinstance(other, PrefixFilter)`` did NOT work properly
        # when running the unit-tests through ``sniffer``. Does this have
        # something to do with ``sniffer`` or is there something wrong with the
        # code of ``config_resolver``? This is a workaround which is incorrect,
        # and could in extreme cases cause problems if there was another
        # filter with the exact same class name and with a ``_prefix`` and
        # ``_separator`` member. They would wrongly be assumed to be the same.
        # I'll assume this won't happen for now.
        return (self.__class__.__name__ == other.__class__.__name__ and
                other._prefix == self._prefix and
                other._separator == self._separator)

    def __repr__(self):
        return 'PrefixFilter(prefix={!r}, separator={!r}>'.format(
            self._prefix, self._separator)

    def filter(self, record):
        record.msg = self._separator.join([self._prefix, record.msg])
        return True


class IncompatibleVersion(Exception):
    """
    This exception is raised if a config file is loaded which has a different
    major version number than expected by the application.
    """
    pass


class NoVersionError(Exception):
    """
    This exception is raised if the application expects a version number to be
    present in the config file but does not find one.
    """
    pass


if sys.hexversion < 0x030000F0:
    # Python 2
    class ConfigResolverBase(SafeConfigParser, object):
        """
        A default "base" object simplifying Python 2 and Python 3
        compatibility.
        """
        pass
else:
    # Python 3
    class ConfigResolverBase(ConfigParser):
        """
        A default "base" object simplifying Python 2 and Python 3
        compatibility.
        """
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
        version checking is performed. Version numbers are parsed using
        :py:class:`distutils.version.StrictVersion`
    """

    def __init__(self, group_name, app_name, search_path=None,
                 filename='app.ini', require_load=False, version=None,
                 **kwargs):
        super(Config, self).__init__(**kwargs)
        self._log = logging.getLogger('{}.{}.{}'.format(__name__,
                                                        group_name,
                                                        app_name))
        self._prefix_filter = PrefixFilter('group={}:app={}'.format(
            group_name, app_name), separator=':')
        if self._prefix_filter not in self._log.filters:
            self._log.addFilter(self._prefix_filter)

        self.version = version and StrictVersion(version) or None
        self.config = None
        self.group_name = group_name
        self.app_name = app_name
        self.search_path = search_path
        self.filename = filename
        self.loaded_files = []
        self.active_path = []
        self.env_path_name = "%s_%s_PATH" % (
            self.group_name.upper(),
            self.app_name.upper())
        self.env_filename_name = "%s_%s_FILENAME" % (
            self.group_name.upper(),
            self.app_name.upper())
        self.load(require_load=require_load)

    def get_xdg_dirs(self):
        """
        Returns a list of paths specified by the XDG_CONFIG_DIRS environment
        variable or the appropriate default.

        The list is sorted by precedence, with the most important item coming
        *last* (required by the existing config_resolver logic).
        """
        config_dirs = getenv('XDG_CONFIG_DIRS', '')
        if config_dirs:
            self._log.debug('XDG_CONFIG_DIRS is set to %r', config_dirs)
            output = []
            for path in reversed(config_dirs.split(':')):
                output.append(join(path, self.group_name, self.app_name))
            return output
        else:
            return ['/etc/xdg/%s/%s' % (self.group_name, self.app_name)]

    def get_xdg_home(self):
        """
        Returns the value specified in the XDG_CONFIG_HOME environment variable
        or the appropriate default.
        """
        config_home = getenv('XDG_CONFIG_HOME', '')
        if config_home:
            self._log.debug('XDG_CONFIG_HOME is set to %r', config_home)
            return expanduser(join(config_home, self.group_name,
                                   self.app_name))
        else:
            return expanduser('~/.config/%s/%s' % (self.group_name,
                                                   self.app_name))

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
            self._log.info('Configuration filename was overridden with {0!r} '
                           'by the environment variable {1}.'.format(
                               env_filename, self.env_filename_name))
            config_filename = env_filename

        return config_filename

    def _effective_path(self):
        """
        Returns a list of paths to search for config files in reverse order of
        precedence.  In other words: the last path element will override the
        settings from the first one.
        """
        # default search path
        path = (['/etc/%s/%s' % (self.group_name, self.app_name)] +
                self.get_xdg_dirs() +
                [expanduser('~/.%s/%s' % (self.group_name, self.app_name)),
                 self.get_xdg_home(),
                 join(getcwd(), '.{}'.format(self.group_name), self.app_name)])

        # If a path was passed directly to this instance, override the path.
        if self.search_path:
            path = self.search_path.split(pathsep)

        # Next, consider the environment variables...
        env_path = getenv(self.env_path_name)

        if env_path and env_path.startswith('+'):
            # If prefixed with a '+', append the path elements
            additional_paths = env_path[1:].split(pathsep)
            self._log.info('Search path extended with {0!r} by the '
                           'environment variable {1}.'.format(
                               additional_paths, self.env_path_name))
            path.extend(additional_paths)
        elif env_path:
            # Otherwise, override again. This takes absolute precedence.
            self._log.info("Configuration search path was overridden with "
                           "{0!r} by the environment variable {1!r}.".format(
                               env_path,
                               self.env_path_name))
            path = env_path.split(pathsep)

        return path

    def check_file(self, filename):
        """
        Check if ``filename`` can be read. Will return a 2-tuple containing a
        boolean if the file can be read, and a string containing an
        error/warning message.

        If the status is "True", then the message should be considered a
        warning. Otherwise it should be considered an error.
        """
        if not exists(filename):
            return False, 'File does not exist'

        # Check if the file is version-compatible with this instance.
        new_config = ConfigResolverBase()
        new_config.read(filename)
        if self.version and not new_config.has_option('meta', 'version'):
            # self.version is set, so we MUST have a version in the file!
            raise NoVersionError(
                "The config option 'meta.version' is missing in {}. The "
                "application expects version {}!".format(filename,
                                                         self.version))
        elif not self.version and new_config.has_option('meta', 'version'):
            # Automatically "lock-in" a version number if one is found.
            # This prevents loading a chain of config files with incompatible
            # version numbers!
            self.version = StrictVersion(new_config.get('meta', 'version'))
            self._log.info('%r contains a version number, but the config '
                           'instance was not created with a version '
                           'restriction. Will set version number to "%s" to '
                           'prevent accidents!',
                           filename, self.version)
        elif self.version:
            # This instance expected a certain version. We need to check the
            # version in the file and compare.
            file_version = new_config.get('meta', 'version')
            major, minor, _ = StrictVersion(file_version).version
            expected_major, expected_minor, _ = self.version.version
            if expected_major != major:
                reason = (
                    'Invalid major version number. Expected %r, got %r!' % (
                        str(self.version),
                        file_version))
                return False, reason

            if expected_minor != minor:
                return True, (
                    'Mismatching minor version number. Expected %r, got %r!' % (
                        str(self.version),
                        file_version))

        return True, ''

    def get(self, section, option, **kwargs):
        """
        Overrides :py:meth:`configparser.ConfigParser.get`.

        In addition to ``section`` and ``option``, this call takes an optional
        ``default`` value. This behaviour works in *addition* to the
        :py:class:`configparser.ConfigParser` default mechanism. Note that
        a default value from ``ConfigParser`` takes precedence.

        The reason this additional functionality is added, is because the
        defaults of :py:class:`configparser.ConfigParser` are not dependent
        on sections. If you specify a default for the option ``test``, then
        this value will be returned for both ``section1.test`` and for
        ``section2.test``. Using the default on the ``get`` call gives you more
        fine-grained control over this.

        Also note, that if a default value was used, it will be logged with
        level ``logging.DEBUG``.

        :param section: The config file section.
        :param option: The option name.
        :param kwargs: These keyword args are passed through to
                       :py:meth:`configparser.ConfigParser.get`.
        """
        if "default" in kwargs:
            default = kwargs.pop("default")
            have_default = True
        else:
            have_default = False

        try:
            value = super(Config, self).get(section, option, **kwargs)
            return value
        except (NoSectionError, NoOptionError) as exc:
            if have_default:
                self._log.debug("{0}: Returning default value {1!r}".format(
                    exc,
                    default))
                return default
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
            self._log.debug('Returning cached config instance. Use '
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
                if cause:
                    self._log.warning(cause)
                self._log.info('%s config from %s' % (
                    self.loaded_files and 'Updating' or 'Loading initial',
                    conf_name))
                self.read(conf_name)
                if conf_name == expanduser("~/.%s/%s/%s" % (
                        self.group_name, self.app_name, self.filename)):
                    self._log.warning(
                        "DEPRECATION WARNING: The file "
                        "'%s/.%s/%s/app.ini' was loaded. The XDG "
                        "Basedir standard requires this file to be in "
                        "'%s/.config/%s/%s/app.ini'! This location "
                        "will no longer be parsed in a future version of "
                        "config_resolver! You can already (and should) move "
                        "the file!", expanduser("~"), self.group_name,
                        self.app_name, expanduser("~"), self.group_name,
                        self.app_name)
                self.loaded_files.append(conf_name)
            else:
                self._log.error('Unable to read %r (%s)' % (conf_name, cause))

        if not self.loaded_files and not require_load:
            self._log.warning(
                "No config file named %s found! Search path was %r" % (
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
            msg = "File %r is not secure enough. Change it's mode to 600"
            self._log.warning(msg, filename)
            return False, msg
        else:
            return True, ''
