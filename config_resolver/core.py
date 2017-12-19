"""
config_resolver provides a ``Config`` class, which looks up common locations
for config files and loads them if found. It provides a framework independed
way of handling configuration files. Additional care has been taken to allow
the end-user of the application to override this lookup process.
"""
from .exc import NoVersionError
from .util import (
    PrefixFilter,
)
from collections import namedtuple
from configparser import ConfigParser
from os import getenv, pathsep, getcwd, stat as get_stat
from os.path import expanduser, exists, join, abspath
import logging
import stat
from distutils.version import StrictVersion


ConfigID = namedtuple('ConfigID', 'group app')


def get_config(*args, **kwargs):
    '''
    Factory function to retrieve new config instances.

    All arguments are currently passed on to either :py:class:`~.Config` or
    :py:class:`~.SecuredConfig`. Which one is chosen depends on the ``secure``
    kwarg. If it is True then a ``SecuredConfig`` will be returned. Otherwise
    (or if missing) it will return a normal ``Config`` instance.
    '''
    is_secure = kwargs.pop('secure', False)
    combined_args = [ConfigID(args[0], args[1])] + list(args[2:])
    if is_secure:
        return SecuredConfig(*combined_args, **kwargs)
    else:
        return Config(*combined_args, **kwargs)


def prefixed_logger(config_id):
    '''
    Returns a log instance for a given group- & app-name pair.
    '''
    log = logging.getLogger('config_resolver.{}.{}'.format(
        config_id.group,
        config_id.app))
    prefix_filter = PrefixFilter('group={}:app={}'.format(
        config_id.group, config_id.app), separator=':')
    if prefix_filter not in log.filters:
        log.addFilter(prefix_filter)
    return log


def get_xdg_dirs(config_id):
    """
    Returns a list of paths specified by the XDG_CONFIG_DIRS environment
    variable or the appropriate default.

    The list is sorted by precedence, with the most important item coming
    *last* (required by the existing config_resolver logic).
    """
    log = prefixed_logger(config_id)
    config_dirs = getenv('XDG_CONFIG_DIRS', '')
    if config_dirs:
        log.debug('XDG_CONFIG_DIRS is set to %r', config_dirs)
        output = []
        for path in reversed(config_dirs.split(':')):
            output.append(join(path, config_id.group, config_id.app))
        return output
    return ['/etc/xdg/%s/%s' % (config_id.group, config_id.app)]


def get_xdg_home(config_id):
    """
    Returns the value specified in the XDG_CONFIG_HOME environment variable
    or the appropriate default.
    """
    log = prefixed_logger(config_id)
    config_home = getenv('XDG_CONFIG_HOME', '')
    if config_home:
        log.debug('XDG_CONFIG_HOME is set to %r', config_home)
        return expanduser(join(config_home, config_id.group, config_id.app))
    return expanduser('~/.config/%s/%s' % (config_id.group, config_id.app))


def effective_path(config_id, search_path=''):
    """
    Returns a list of paths to search for config files in reverse order of
    precedence. In other words: the last path element will override the
    settings from the first one.
    """
    log = prefixed_logger(config_id)

    # default search path
    path = (['/etc/%s/%s' % (config_id.group, config_id.app)] +
            get_xdg_dirs(config_id) +
            [get_xdg_home(config_id),
             join(getcwd(), '.{}'.format(config_id.group), config_id.app)])

    # If a path was passed directly to this instance, override the path.
    if search_path:
        path = search_path.split(pathsep)

    # Next, consider the environment variables...
    env_path_name = "%s_%s_PATH" % (
        config_id.group.upper(), config_id.app.upper())
    env_path = getenv(env_path_name)

    if env_path and env_path.startswith('+'):
        # If prefixed with a '+', append the path elements
        additional_paths = env_path[1:].split(pathsep)
        log.info('Search path extended with %r by the environment '
                 'variable %s.',
                 additional_paths,
                 env_path_name)
        path.extend(additional_paths)
    elif env_path:
        # Otherwise, override again. This takes absolute precedence.
        log.info("Configuration search path was overridden with "
                 "%r by the environment variable %r.",
                 env_path,
                 env_path_name)
        path = env_path.split(pathsep)

    return path


def find_files(config_id, search_path=None, filename='app.ini', secure=False):
    """
    Looks for files in default locations. Returns an iterator of filenames.

    :param config_id: A "ConfigID" object used to identify the config folder.
    :param search_path: The path can use OS specific separators (f.ex.: ``:``
        on posix, ``;`` on windows) to specify multiple folders. These
        folders will be searched in the specified order.
    :param filename: The name of the file we search for.
    """
    log = prefixed_logger(config_id)

    path = effective_path(config_id, search_path)
    config_filename = effective_filename(config_id, filename)

    # Next, use the resolved path to find the filenames. Keep track of
    # which files we loaded in order to inform the user.
    for dirname in path:
        conf_name = join(dirname, config_filename)
        if is_readable(config_id, conf_name, secure=secure):
            log.info('Found file at %s', conf_name)
            yield conf_name


def effective_filename(config_id, custom_filename):
    """
    Returns the filename which is effectively used by the application. If
    overridden by an environment variable, it will return that filename.
    """
    log = prefixed_logger(config_id)

    # same logic for the configuration filename. First, check if we were
    # initialized with a filename...
    config_filename = None
    if custom_filename:
        config_filename = custom_filename

    # ... next, take the value from the environment
    env_filename = getenv(env_name(config_id))
    if env_filename:
        log.info('Configuration filename was overridden with %r '
                 'by the environment variable %s.',
                 env_filename,
                 env_name(config_id))
        config_filename = env_filename

    return config_filename


def env_name(config_id):
    return "%s_%s_FILENAME" % (config_id.group.upper(), config_id.app.upper())


def is_readable(config_id, filename, version=None, secure=False):
    """
    Check if ``filename`` can be read. Will return boolean which is True if
    the file can be read, False otherwise.
    """
    log = prefixed_logger(config_id)

    if not exists(filename):
        return False

    insecure_readable = True
    file_version = None

    # Check if the file is version-compatible with this instance.
    new_config = ConfigParser()
    new_config.read(filename)
    if version and not new_config.has_option('meta', 'version'):
        # version is set, so we MUST have a version in the file!
        raise NoVersionError(
            "The config option 'meta.version' is missing in {}. The "
            "application expects version {}!".format(filename, version))
    elif not version and new_config.has_option('meta', 'version'):
        # Automatically "lock-in" a version number if one is found.
        # This prevents loading a chain of config files with incompatible
        # version numbers!
        # TODO: This is no longer "locked in" as it's no longer a class member!
        version = StrictVersion(new_config.get('meta', 'version'))
        log.info('%r contains a version number, but the config '
                 'instance was not created with a version '
                 'restriction. Will set version number to "%s" to '
                 'prevent accidents!',
                 filename, version)
    elif version:
        # This instance expected a certain version. We need to check the
        # version in the file and compare.
        file_version = new_config.get('meta', 'version')
        major, minor, _ = StrictVersion(file_version).version
        expected_major, expected_minor, _ = version.version
        if expected_major != major:
            log.error(
                'Invalid major version number in %r. Expected %r, got %r!',
                abspath(filename),
                str(version),
                file_version)
            insecure_readable = False
        elif expected_minor != minor:
            log.warning(
                'Mismatching minor version number in %r. '
                'Expected %r, got %r!',
                abspath(filename),
                str(version),
                file_version)
            insecure_readable = True

    if insecure_readable and secure:
        mode = get_stat(filename).st_mode
        if (mode & stat.S_IRGRP) or (mode & stat.S_IROTH):
            msg = "File %r is not secure enough. Change it's mode to 600"
            log.warning(msg, filename)
            return False
    return insecure_readable


class Config(ConfigParser):  # pylint: disable = too-many-ancestors
    """
    Initialises a config object with files found on the search path.

    If files are found one more than one location on the search path, the files
    will be loaded incrementally. This means that each subsequent config file
    will extend/override existing value and that the last file will take
    precedence.

    :param config_id: Forwarded to :py:func:`.find_files`.
    :param search_path: Forwarded to :py:func:`.find_files`.
    :param filename: Forwarded to :py:func:`.find_files`.
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

    SECURE = False

    def __init__(self, config_id, search_path=None,
                 filename='app.ini', require_load=False, version=None,
                 **kwargs):
        # pylint: disable = too-many-arguments
        super(Config, self).__init__(**kwargs)
        self._log = prefixed_logger(config_id)

        self.version = StrictVersion(version) if version else None
        self.config = None
        self.config_id = config_id
        self.group_name = config_id.group
        self.app_name = config_id.app
        self.filename = filename
        self.loaded_files = []
        self.load(search_path, require_load=require_load)

    def load(self, search_path, reload=False, require_load=False):
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

        files = find_files(
            self.config_id,
            search_path,
            self.filename,
            self.SECURE)

        loaded_files = list(files)  # TODO this is incorrect!
        if not loaded_files and not require_load:
            self._log.warning(
                "No config file named %s found! Search path was %r",
                self.filename,
                search_path)
        elif not loaded_files and require_load:
            raise IOError("No config file named %s found! Search path "
                          "was %r" % (self.filename, search_path))

        # XXX -- begin
        path = effective_path(self.config_id, search_path)
        config_filename = effective_filename(self.config_id, self.filename)

        # Next, use the resolved path to find the filenames. Keep track of
        # which files we loaded in order to inform the user.
        self.active_path = [join(_, config_filename) for _ in path]
        for dirname in path:
            conf_name = join(dirname, config_filename)
            readable = is_readable(
                self.config_id,
                conf_name,
                version=self.version,
                secure=self.SECURE
            )
            if readable:
                action = 'Updating' if self.loaded_files else 'Loading initial'
                self._log.info('%s config from %s', action, conf_name)
                self.read(conf_name)
                self.loaded_files.append(conf_name)

        if not self.loaded_files and not require_load:
            self._log.warning(
                "No config file named %s found! Search path was %r",
                config_filename,
                path)
        elif not self.loaded_files and require_load:
            raise IOError("No config file named %s found! Search path "
                          "was %r" % (config_filename, path))
        # XXX -- end


class SecuredConfig(Config):  # pylint: disable = too-many-ancestors
    """
    A subclass of :py:class:`.Config` which will refuse to load config files
    which are read able by other users than the owner.
    """

    SECURE = True
