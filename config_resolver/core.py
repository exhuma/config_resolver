"""
Core functionality of :py:mod:`config_resolver`
"""

import logging
import stat
from collections import namedtuple
from functools import lru_cache
from os import stat as get_stat
from os import getcwd, getenv, pathsep
from os.path import abspath, exists, expanduser, join

from config_resolver.dirty import StrictVersion
from config_resolver.handler import ini

from .exc import NoVersionError
from .util import PrefixFilter

ConfigID = namedtuple('ConfigID', 'group app')
LookupResult = namedtuple('LookupResult', 'config meta')
LookupMetadata = namedtuple('LookupMetadata', [
    'active_path',
    'loaded_files',
    'config_id',
    'prefix_filter'
])
FileReadability = namedtuple(
    'FileReadability', 'is_readable filename reason version')


def from_string(data, handler=None):
    '''
    Load a config from the string value in *data*. *handler* can be used to
    specify a custom parser/handler.
    '''
    handler = handler or ini
    # TODO: This still does not do any version checking!
    new_config = handler.from_string(data)
    return LookupResult(new_config, LookupMetadata(
        '<unknown>',
        '<unknown>',
        ConfigID('<unknown>', '<unknown>'),
        None
    ))


def get_config(group_name, app_name, lookup_options=None, handler=None):
    '''
    Factory function to retrieve new config instances.

    *group_name* and *app_name* are used to determine the folder locations. We
    always assume a structure like
    ``<group_name>/<app_name>/<filename>.<extension>``.

    *lookup_options* is a dictionary with the following optional keys:

    **search_path** (default=``[]``)
        A list of folders that should be searched for config files. The order
        here is relevant. The folders will be searched in order, and each file
        which is found will be loaded by the *handler*.

    **filename** (default=``'app.ini'``)
        The *basename* of the file which should be loaded (f.ex.: ``db.ini``)

    **require_load** (default=``False``)
        A boolean value which determines what happens if *no* file was loaded.
        If this is set to ``True`` the call to ``get_config`` will raise an
        exception if no file was found. Otherwise it will simply log a warning.

    **version** (default=``None``)
        This can be a string in the form ``<major>.<minor>``. If specified, the
        lookup process will request a version number from the *handler* for each
        file found. The version in the file will be compared with this value. If
        the minor-number differs, the file will be loaded, but a warning will be
        logged. If the major number differs, the file will be skipped and an
        error will be logged. If the value is left unset, no version checking
        will be performed.

        How the version has to be stored in the config file depends on the
        handler.

    **secure** (default=``False``)
        If set to ``True``, files which are world-readable will be ignored. The
        idea here is nicked from the way SSH handles files with sensitive data.
        It forces you to have secure file-access rights because the file will be
        skipped if the rights are too open.
    '''
    handler = handler or ini
    config_id = ConfigID(group_name, app_name)
    log, prefix_filter = prefixed_logger(config_id)

    default_options = {
        'search_path': [],
        'filename': handler.DEFAULT_FILENAME,
        'require_load': False,
        'version': None,
        'secure': False,
    }
    if lookup_options:
        default_options.update(lookup_options)

    secure = default_options['secure']
    require_load = default_options['require_load']
    search_path = default_options['search_path']
    filename = default_options['filename']
    filename = effective_filename(config_id, filename)
    requested_version = default_options['version']
    if requested_version:
        version = StrictVersion(requested_version)
    else:
        version = None

    loaded_files = []

    search_path = effective_path(config_id, search_path)

    # Store the complete list of all inspected items
    active_path = [join(_, filename) for _ in search_path]

    output = handler.empty()
    found_files = find_files(config_id, search_path, filename)

    current_version = version
    for filename in found_files:
        readability = is_readable(config_id, filename, current_version, secure,
                                  handler)
        if not current_version and readability.version:
            # Automatically "lock-in" a version number if one is found.
            # This prevents loading a chain of config files with incompatible
            # version numbers!
            log.info('%r contains a version number, but the config '
                     'instance was not created with a version '
                     'restriction. Will set version number to "%s" to '
                     'prevent accidents!',
                     filename, readability.version)
            current_version = readability.version
        if readability.is_readable:
            action = 'Updating' if loaded_files else 'Loading initial'
            log.info('%s config from %s', action, filename)
            handler.update_from_file(output, filename)
            loaded_files.append(filename)
        else:
            log.warning('Skipping unreadable file %s (%s)', filename,
                        readability.reason)

    if not loaded_files and not require_load:
        log.warning(
            "No config file named %s found! Search path was %r",
            filename,
            search_path)
    elif not loaded_files and require_load:
        raise IOError("No config file named %s found! Search path "
                      "was %r" % (filename, search_path))

    return LookupResult(output, LookupMetadata(
        active_path,
        loaded_files,
        config_id,
        prefix_filter
    ))


@lru_cache(5)
def prefixed_logger(config_id):
    '''
    Returns a log instance and prefix filter for a given group- & app-name pair.

    The call to this function is cached to ensure we only have one instance in
    memory.
    '''
    log = logging.getLogger('config_resolver.{}.{}'.format(
        config_id.group,
        config_id.app))
    prefix_filter = PrefixFilter('group={}:app={}'.format(
        config_id.group, config_id.app), separator=':')
    if prefix_filter not in log.filters:
        log.addFilter(prefix_filter)
    return log, prefix_filter


def get_xdg_dirs(config_id):
    """
    Returns a list of paths specified by the XDG_CONFIG_DIRS environment
    variable or the appropriate default. See :ref:`xdg-spec` for details.

    The list is sorted by precedence, with the most important item coming
    *last* (required by the existing config_resolver logic).

    The value in *config_id* is used to determine the sub-folder structure.
    """
    log, _ = prefixed_logger(config_id)
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
    or the appropriate default. See :ref:`xdg-spec` for details.
    """
    log, _ = prefixed_logger(config_id)
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

    The value in *config_id* determines the sub-folder structure.

    If *search_path* is specified, that value should have the OS specific
    path-separator (``:`` or ``;``). This will override the default path.
    Subsequently the value of the environment variable
    ``<GROUP_NAME>_<APP_NAME>_PATH`` will be inspected. If this value is set, it
    will be used instead of anything found previously unless the value is
    prefixed with a ``+`` sign. In that case it will be appended to the end of
    the list.
    """
    log, _ = prefixed_logger(config_id)

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
                 env_path,
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


def find_files(config_id, search_path=None, filename=None):
    """
    Looks for files in default locations. Returns an iterator of filenames.

    :param config_id: A "ConfigID" object used to identify the config folder.
    :param search_path: A list of paths to search for files.
    :param filename: The name of the file we search for.
    """
    config_filename = effective_filename(config_id, filename)

    # Next, use the resolved path to find the filenames. Keep track of
    # which files we loaded in order to inform the user.
    for dirname in search_path:
        conf_name = join(dirname, config_filename)
        yield conf_name


def effective_filename(config_id, config_filename):
    """
    Returns the filename which is effectively used by the application. If
    overridden by an environment variable, it will return that filename.

    *config_id* is used to determine the name of the variable. If that does not
    return a value, *config_filename* will be returned instead.
    """
    log, _ = prefixed_logger(config_id)

    env_filename = getenv(env_name(config_id))
    if env_filename:
        log.info('Configuration filename was overridden with %r '
                 'by the environment variable %s.',
                 env_filename,
                 env_name(config_id))
        config_filename = env_filename

    return config_filename


def env_name(config_id):
    '''
    Return the name of the environment variable which contains the file-name to
    load.
    '''
    return "%s_%s_FILENAME" % (config_id.group.upper(), config_id.app.upper())


def is_readable(config_id, filename, version=None, secure=False, handler=None):
    """
    Check if ``filename`` can be read. Will return boolean which is True if
    the file can be read, False otherwise.

    :param filename: The exact filename which should be checked.
    :param version: The expected version, that should be found in the file.
    :param secure: Whether we should avoid loading insecure files or not.
    :param handler: The handler to be used to open and parse the file.
    """
    log, _ = prefixed_logger(config_id)
    handler = handler or ini

    if not exists(filename):
        return FileReadability(False, filename, 'File not found', None)
    log.debug('Checking if %s is readable.', filename)

    insecure_readable = True
    unreadable_reason = '<unknown>'

    # Check if the file is version-compatible with this instance.
    config_instance = handler.from_filename(filename)
    instance_version = handler.get_version(config_instance)

    if version and not instance_version:
        # version is set, so we MUST have a version in the file!
        raise NoVersionError(
            "The config option 'meta.version' is missing in {}. The "
            "application expects version {}!".format(filename, version))
    elif version:
        # The user expected a certain version. We need to check the version in
        # the file and compare.
        major, minor, _ = instance_version.version
        expected_major, expected_minor, _ = version.version
        if expected_major != major:
            msg = 'Invalid major version number in %r. Expected %r, got %r!'
            log.error(
                msg,
                abspath(filename),
                str(version),
                instance_version)
            insecure_readable = False
            unreadable_reason = msg
        elif expected_minor != minor:
            msg = 'Mismatching minor version number in %r. Expected %r, got %r!'
            log.warning(
                msg,
                abspath(filename),
                str(version),
                instance_version)
            insecure_readable = True
            unreadable_reason = msg

    if insecure_readable and secure:
        mode = get_stat(filename).st_mode
        if (mode & stat.S_IRGRP) or (mode & stat.S_IROTH):
            msg = "File %r is not secure enough. Change it's mode to 600"
            log.warning(msg, filename)
            return FileReadability(False, filename, msg, instance_version)
    return FileReadability(insecure_readable, filename, unreadable_reason,
                           instance_version)
