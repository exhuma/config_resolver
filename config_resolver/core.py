"""
config_resolver provides a ``Config`` class, which looks up common locations
for config files and loads them if found. It provides a framework independed
way of handling configuration files. Additional care has been taken to allow
the end-user of the application to override this lookup process.
"""
try:
    from ConfigParser import (  # type: ignore
        SafeConfigParser,
        NoOptionError,
        NoSectionError
    )
except ImportError:
    from configparser import ConfigParser, NoOptionError, NoSectionError

import logging
import stat
import sys
from collections import namedtuple
from distutils.version import StrictVersion
from os import getcwd, getenv, pathsep
from os import stat as get_stat
from os.path import abspath, exists, expanduser, join
from typing import Any, Dict, List, Optional
from warnings import warn

from .exc import NoVersionError
from .util import PrefixFilter

__version__ = '4.3.3'


ConfigID = namedtuple('ConfigID', 'group app')
LookupResult = namedtuple('LookupResult', 'config meta')
LookupMetadata = namedtuple('LookupMetadata', [
    'active_path',
    'loaded_files',
    'config_id',
    'prefix_filter'
])


if sys.hexversion < 0x030000F0:
    # Python 2
    # pylint: disable = too-few-public-methods
    class ConfigResolverBase(SafeConfigParser, object):  # type: ignore
        """
        A default "base" object simplifying Python 2 and Python 3
        compatibility.
        """
else:
    # Python 3
    # pylint: disable = too-few-public-methods
    class ConfigResolverBase(ConfigParser):  # type: ignore # pylint: disable = too-many-ancestors
        """
        A default "base" object simplifying Python 2 and Python 3
        compatibility.
        """


def get_new_call(group_name, app_name, search_path, filename, require_load,
                 version, secure):
    # type: (str, str, Optional[str], str, bool, Optional[str], bool) -> str
    '''
    Build a call to use the new ``get_config`` function from args passed to
    ``Config.__init__``.
    '''
    new_call_kwargs = {
        'group_name': group_name,
        'filename': filename
    }  # type: Dict[str, Any]
    new_call_lookup_options = {}  # type: Dict[str, Any]
    new_call_lookup_options['secure'] = secure
    if search_path:
        new_call_lookup_options['search_path'] = search_path
    if require_load:
        new_call_lookup_options['require_load'] = require_load
    if version:
        new_call_lookup_options['version'] = version
    if new_call_lookup_options:
        new_call_kwargs['lookup_options'] = new_call_lookup_options

    output = build_call_str('get_config', (app_name,), new_call_kwargs)
    return output


def build_call_str(prefix, args, kwargs):
    # type: (str, Any, Any) -> str
    '''
    Build a callable Python string for a function call. The output will be
    combined similar to this template::

        <prefix>(<args>, <kwargs>)

    Example::

        >>> build_call_str('foo', (1, 2), {'a': '10'})
        "foo(1, 2, a='10')"
    '''
    kwargs_str = ', '.join(['%s=%r' % (key, value) for key, value in
                            kwargs.items()])
    args_str = ', '.join([repr(arg) for arg in args])
    output = [prefix, '(']
    if args:
        output.append(args_str)
    if args and kwargs:
        output.append(', ')
    if kwargs:
        output.append(kwargs_str)
    output.append(')')
    return ''.join(output)


class Config(ConfigResolverBase):  # pylint: disable = too-many-ancestors
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
        versioned config instance. A versioned instance will only load config
        files which have the same major version. On mismatch an error is logged
        and the file is skipped. If the minor version differs the file will be
        loaded, but issue a warning log. Version numbers are parsed using
        :py:class:`distutils.version.StrictVersion`
    """
    # pylint: disable = too-many-instance-attributes

    def __init__(self, group_name, app_name, search_path=None,
                 filename='app.ini', require_load=False, version=None,
                 **kwargs):
        # type: (str, str, Optional[str], str, bool, Optional[str], Any) -> None
        # pylint: disable = too-many-arguments
        super(Config, self).__init__(**kwargs)

        # Calling this constructor is deprecated and will disappear in version
        # 5.0
        secure = isinstance(self, SecuredConfig)
        new_call = get_new_call(group_name, app_name, search_path, filename,
                                require_load, version, secure)
        warn('Using the "Config(...)" constructor will be '
             'deprecated in version 5.0! Use "get_config(...)" instead. '
             'Your call should be replaceable with: %r' % (new_call),
             DeprecationWarning,
             stacklevel=2)

        # --- end of deprecation check --------------------------------------

        self._log = logging.getLogger('{}.{}.{}'.format('config_resolver',
                                                        group_name,
                                                        app_name))
        self._prefix_filter = PrefixFilter('group={}:app={}'.format(
            group_name, app_name), separator=':')
        if self._prefix_filter not in self._log.filters:
            self._log.addFilter(self._prefix_filter)

        self.version = StrictVersion(version) if version else None
        self.config = None
        self.group_name = group_name
        self.app_name = app_name
        self.search_path = search_path
        self.filename = filename
        self._loaded_files = []  # type: List[str]
        self._active_path = []  # type: List[str]
        self.env_path_name = "%s_%s_PATH" % (
            self.group_name.upper(),
            self.app_name.upper())
        self.env_filename_name = "%s_%s_FILENAME" % (
            self.group_name.upper(),
            self.app_name.upper())
        self.require_load = require_load
        self.load(require_load=require_load)

    @property
    def loaded_files(self):
        # type: () -> List[str]
        warn('The "loaded_files" attribute moved to the "meta" return '
             'value of "get_config". Use `get_config(...).meta.loaded_files`',
             DeprecationWarning, stacklevel=2)
        return self._loaded_files

    @property
    def active_path(self):
        # type: () -> List[str]
        warn('The "active_path" attribute moved to the "meta" return '
             'value of "get_config". Use `get_config(...).meta.active_path`',
             DeprecationWarning, stacklevel=2)
        return self._active_path

    def get_xdg_dirs(self):
        # type: () -> List[str]
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
        return ['/etc/xdg/%s/%s' % (self.group_name, self.app_name)]

    def get_xdg_home(self):
        # type: () -> str
        """
        Returns the value specified in the XDG_CONFIG_HOME environment variable
        or the appropriate default.
        """
        config_home = getenv('XDG_CONFIG_HOME', '')
        if config_home:
            self._log.debug('XDG_CONFIG_HOME is set to %r', config_home)
            return expanduser(join(config_home, self.group_name, self.app_name))
        return expanduser('~/.config/%s/%s' % (self.group_name, self.app_name))

    def _effective_filename(self):
        # type: () -> str
        """
        Returns the filename which is effectively used by the application. If
        overridden by an environment variable, it will return that filename.
        """
        # same logic for the configuration filename. First, check if we were
        # initialized with a filename...
        config_filename = ''
        if self.filename:
            config_filename = self.filename

        # ... next, take the value from the environment
        env_filename = getenv(self.env_filename_name)
        if env_filename:
            self._log.info('Configuration filename was overridden with %r '
                           'by the environment variable %s.',
                           env_filename,
                           self.env_filename_name)
            config_filename = env_filename

        return config_filename

    def _effective_path(self):
        # type: () -> List[str]
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
            self._log.info('Search path extended with %r by the environment '
                           'variable %s.',
                           additional_paths,
                           self.env_path_name)
            path.extend(additional_paths)
        elif env_path:
            # Otherwise, override again. This takes absolute precedence.
            self._log.info("Configuration search path was overridden with "
                           "%r by the environment variable %r.",
                           env_path,
                           self.env_path_name)
            path = env_path.split(pathsep)

        return path

    def check_file(self, filename):
        # type: (str) -> bool
        """
        Check if ``filename`` can be read. Will return boolean which is True if
        the file can be read, False otherwise.
        """
        if not exists(filename):
            return False

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
                self._log.error(
                    'Invalid major version number in %r. Expected %r, got %r!',
                    abspath(filename),
                    str(self.version),
                    file_version)
                return False

            if expected_minor != minor:
                self._log.warning(
                    'Mismatching minor version number in %r. '
                    'Expected %r, got %r!',
                    abspath(filename),
                    str(self.version),
                    file_version)
                return True
        return True

    def get(self, section, option, **kwargs):  # type: ignore
        # type: (str, str, Any) -> Any
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
            new_kwargs = {'fallback': default}
            new_kwargs.update(kwargs)
            new_call = build_call_str('.get', (section, option), new_kwargs)
            warn('Using the "default" argument to Config.get() will no '
                 'longer work in config_resolver 5.0! Version 5 will return '
                 'standard Python ConfigParser instances which use "fallback" '
                 'instead of "default". Replace your code with "%s"' % new_call,
                 DeprecationWarning,
                 stacklevel=2)
            have_default = True
        else:
            have_default = False

        try:
            value = super(Config, self).get(section, option, **kwargs)
            return value
        except (NoSectionError, NoOptionError) as exc:
            if have_default:
                self._log.debug("%s: Returning default value %r", exc, default)
                return default
            else:
                raise

    def load(self, reload=False, require_load=False):
        # type: (bool, bool) -> None
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
        self._active_path = [join(_, config_filename) for _ in path]
        for dirname in path:
            conf_name = join(dirname, config_filename)
            readable = self.check_file(conf_name)
            if readable:
                action = 'Updating' if self._loaded_files else 'Loading initial'
                self._log.info('%s config from %s', action, conf_name)
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
                self._loaded_files.append(conf_name)

        if not self._loaded_files and not require_load:
            self._log.warning(
                "No config file named %s found! Search path was %r",
                config_filename,
                path)
        elif not self._loaded_files and require_load:
            raise IOError("No config file named %s found! Search path "
                          "was %r" % (config_filename, path))


class SecuredConfig(Config):  # pylint: disable = too-many-ancestors
    """
    A subclass of :py:class:`.Config` which will refuse to load config files
    which are read able by other users than the owner.
    """

    def check_file(self, filename):
        # type: (str) -> bool
        """
        Overrides :py:meth:`.Config.check_file`
        """
        can_read = super(SecuredConfig, self).check_file(filename)
        if not can_read:
            return False

        mode = get_stat(filename).st_mode
        if (mode & stat.S_IRGRP) or (mode & stat.S_IROTH):
            msg = "File %r is not secure enough. Change it's mode to 600"
            self._log.warning(msg, filename)
            return False
        return True


def get_config(app_name, group_name='', filename='',
               lookup_options=None, handler=None):
    # type: (str, str, str, Optional[Dict[str, str]], Optional[Any]) -> LookupResult
    # pylint: disable=protected-access

    lookup_options = lookup_options or {}
    if not lookup_options.pop('secure', False):
        cls = Config
    else:
        cls = SecuredConfig

    search_path = lookup_options.get('search_path', None)
    filename = filename or lookup_options.get('filename') or 'config.ini'
    version = lookup_options.get('version', None)
    require_load = lookup_options.get('require_load', False)

    if 'filename' in lookup_options:
        warn('"filename" should be passed as direct argument to '
             'get_config instead of passing it in '
             '"lookup_options"!)', DeprecationWarning, stacklevel=2)

    cfg = cls(group_name, app_name, search_path=search_path, filename=filename,
              version=version, require_load=require_load)
    output = LookupResult(
        cfg,
        LookupMetadata(
            cfg._active_path,
            cfg._loaded_files,
            ConfigID(group_name, app_name),
            cfg._prefix_filter
        )
    )

    return output
