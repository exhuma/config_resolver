"""
Core functionality of :py:mod:`config_resolver`
"""

import logging
import stat
from functools import lru_cache
from logging import Filter, Logger
from os import getcwd, getenv, pathsep
from os import stat as get_stat
from os.path import abspath, exists, expanduser, join
from typing import (
    Any,
    Dict,
    Generator,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    cast,
)

from packaging.version import Version

from config_resolver.handler.ini import IniHandler

from .exc import NoVersionError
from .handler.base import Handler
from .util import PrefixFilter


class ConfigID(NamedTuple):
    group: str
    app: str


class LookupMetadata(NamedTuple):
    active_path: List[str]
    loaded_files: List[str]
    config_id: ConfigID
    prefix_filter: Optional[Filter]


class LookupResult(NamedTuple):
    config: Any
    meta: LookupMetadata


class FileReadability(NamedTuple):
    is_readable: bool
    filename: str
    reason: str
    version: Optional[Version]


def from_string(
    data: str, handler: Optional[Handler[Any]] = None
) -> LookupResult:
    """
    Load a config from the string value in *data*. *handler* can be used to
    specify a custom parser/handler.
    """
    handler_ = handler or IniHandler
    # TODO: This still does not do any version checking!
    new_config = handler_.from_string(data)
    return LookupResult(
        new_config,
        LookupMetadata(
            ["<unknown>"],
            ["<unknown>"],
            ConfigID("<unknown>", "<unknown>"),
            None,
        ),
    )


def get_config(
    app_name: str,
    group_name: str = "",
    lookup_options: Optional[Dict[str, Any]] = None,
    handler: "Optional[Type[Handler[Any]]]" = None,
) -> LookupResult:
    """
    Factory function to retrieve new config instances.

    *app_name* is the only required argument for config lookups. If nothing else
    is specified, this will trigger a lookup in default XDG locations for a
    config file in a subfolder with that name.

    *group_name* is an optional subfolder which is *prefixed* to the subfolder
    based on the *app_name*. This can be used to group related configurations
    together.

    To summarise the two above paragraphs the relative path (relative to the
    search locations) will be:

    * ``<app_name>/<filename>`` if only *app_name* is given
    * ``<group_name>/<app_name>/<filename>`` if both *app_name* and
      *group_name* are given

    *lookup_options* contains arguments which allow more fine-grained control
    of the lookup process. See below for details.

    The *handler* may be a class which is responsible for loading the config
    file. *config_resolver* uses a ".ini" file handler by default and comes
    bundled with a JSON handler as well. They can be found in the
    :py:module:`config_resolver.handler` package.

    .. note::

        The type of the returned config-object depends on the handler. Each
        handler has its own config type!

    For example, loading JSON files can be achieved using:

    >>> from config_resolver.handler.json import JsonHandler
    >>> get_config("myapp", handler=JsonHandler)

    *lookup_options* is a dictionary with the following optional keys:

    **filename** (default=``''``)
        This can be used to override the default filename of the selected
        handler. If left empty, the handler will be responsible for the
        filename.

    **search_path** (default=``[]``)
        A list of folders that should be searched for config files. The order
        here is relevant. The folders will be searched in order, and each file
        which is found will be loaded by the *handler*. Note that the search
        path should not include *group_name* or *app_name* as they will be
        appended automatically.

    **require_load** (default=``False``)
        A boolean value which determines what happens if *no* file was loaded.
        If this is set to ``True`` the call to ``get_config`` will raise an
        exception if no file was found. Otherwise it will log a debug message.

    **version** (default=``None``)
        This can be a string in the form ``<major>.<minor>``. If specified, the
        lookup process will request a version number from the *handler* for each
        file found. The version in the file will be compared with this value. If
        the minor-number differs, the file will be loaded, but a warning will be
        logged. If the major number differs, the file will be skipped and an
        error will be logged. If the value is left unset, no version checking
        will be performed. If this is left unspecified and a config file is
        encountered with a version number, a sanity check is performed on
        subsequent config-files to ensure that no mismatching major versions
        are loaded in the lookup-chain.

        How the version has to be stored in the config file depends on the
        handler.

    **secure** (default=``False``)
        If set to ``True``, files which are world-readable will be ignored.
        This forces you to have secure file-access rights because the file will
        be skipped if the rights are too open.
    """
    concrete_handler: Type[Handler[Any]] = handler or IniHandler
    config_id = ConfigID(group_name, app_name)
    log, prefix_filter = prefixed_logger(config_id)

    default_options = {
        "search_path": "",
        "filename": concrete_handler.DEFAULT_FILENAME,
        "require_load": False,
        "version": None,
        "secure": False,
    }
    if lookup_options:
        default_options.update(lookup_options)

    secure = cast(bool, default_options["secure"])
    require_load = default_options["require_load"]
    search_path = cast(str, default_options["search_path"])
    filename = cast(str, default_options["filename"])
    filename = effective_filename(config_id, filename)
    requested_version = cast(str, default_options["version"])
    version = None
    if requested_version:
        version = Version(requested_version)

    loaded_files = []  # type: List[str]

    search_path_ = effective_path(config_id, search_path)

    # Store the complete list of all inspected items
    active_path = [join(_, filename) for _ in search_path_]

    output = concrete_handler.empty()
    found_files = find_files(config_id, search_path_, filename)

    current_version = version
    for filename in found_files:
        readability = is_readable(
            config_id, filename, current_version, secure, concrete_handler
        )
        if not current_version and readability.version:
            # Automatically "lock-in" a version number if one is found.
            # This prevents loading a chain of config files with incompatible
            # version numbers!
            log.info(
                "%r contains a version number, but the config "
                "instance was not created with a version "
                'restriction. Will set version number to "%s" to '
                "prevent accidents!",
                filename,
                readability.version,
            )
            current_version = readability.version
        if readability.is_readable:
            action = "Updating" if loaded_files else "Loading initial"
            log.info("%s config from %s", action, filename)
            concrete_handler.update_from_file(output, filename)
            loaded_files.append(filename)
        else:
            log.debug(
                "Skipping unreadable file %s (%s)", filename, readability.reason
            )

    if not loaded_files and not require_load:
        log.debug(
            "No config file named %s found! Search path was %r",
            filename,
            search_path_,
        )
    elif not loaded_files and require_load:
        raise OSError(
            "No config file named %s found! Search path "
            "was %r" % (filename, search_path_)
        )

    return LookupResult(
        output,
        LookupMetadata(active_path, loaded_files, config_id, prefix_filter),
    )


def _is_world_readable(filename: str) -> bool:
    """
    Returns True if the given file is readable by everyone on the system (has
    readable flags for "group" and "other"), False otherwise
    """
    mode = get_stat(filename).st_mode
    matching_modes = (mode & stat.S_IRGRP) or (mode & stat.S_IROTH)
    return bool(matching_modes)


@lru_cache(5)
def prefixed_logger(
    config_id: Optional[ConfigID],
) -> Tuple[Logger, Optional[Filter]]:
    """
    Returns a log instance and prefix filter for a given group- & app-name pair.

    It applies a filter to the logger which prefixes the log messages with
    group- and application-name from the config.

    The call to this function is cached to ensure we only have one instance in
    memory.
    """
    if config_id is None:
        log = logging.getLogger("config_resolver")
        return log, None
    log = logging.getLogger(
        "config_resolver.{}.{}".format(config_id.group, config_id.app)
    )
    prefix_filter = PrefixFilter(
        "group={}:app={}".format(config_id.group, config_id.app), separator=":"
    )
    if prefix_filter not in log.filters:
        log.addFilter(prefix_filter)
    return log, prefix_filter


def get_xdg_dirs(config_id: ConfigID) -> List[str]:
    """
    Returns a list of paths specified by the XDG_CONFIG_DIRS environment
    variable or the appropriate default. See :ref:`xdg-spec` for details.

    The list is sorted by precedence, with the most important item coming
    *last* (required by the existing config_resolver logic).

    The value in *config_id* is used to determine the sub-folder structure.
    """
    log, _ = prefixed_logger(config_id)
    config_dirs = getenv("XDG_CONFIG_DIRS", "")
    if config_dirs:
        log.debug("XDG_CONFIG_DIRS is set to %r", config_dirs)
        output: List[str] = []
        for path in reversed(config_dirs.split(":")):
            output.append(join(path, config_id.group, config_id.app))
        return output
    return [f"/etc/xdg/{config_id.group}/{config_id.app}"]


def get_xdg_home(config_id: ConfigID) -> str:
    """
    Returns the value specified in the XDG_CONFIG_HOME environment variable
    or the appropriate default. See :ref:`xdg-spec` for details.
    """
    log, _ = prefixed_logger(config_id)
    config_home = getenv("XDG_CONFIG_HOME", "")
    if config_home:
        log.debug("XDG_CONFIG_HOME is set to %r", config_home)
        return expanduser(join(config_home, config_id.group, config_id.app))
    return expanduser(f"~/.config/{config_id.group}/{config_id.app}")


def effective_path(config_id: ConfigID, search_path: str = "") -> List[str]:
    """
    Returns a list of paths to search for config files in order of
    increasing precedence: the last item in the list will override values of
    earlier items.

    The value in *config_id* determines the sub-folder structure.

    If *search_path* is specified, that value should have the OS specific
    path-separator (``:`` or ``;``) and will completely override the default
    search order. If it is left empty, the search order is dictated by the
    XDG standard.

    As a "last-resort" override, the value of the environment variable
    ``<GROUP_NAME>_<APP_NAME>_PATH`` will be inspected. If this value is set, it
    will be used instead of *anything* found previously (XDG paths,
    ``search_path`` value) unless the value is prefixed with a ``+`` sign. In
    that case it will be *appended* to the end of the list.

    Examples::

        >>> # Search the default XDG paths (and the CWD)
        >>> effective_path(config_id)

        >>> # Search only in "/etc/myapp"
        >>> effective_path(config_id, search_path="/etc/myapp")

        >>> # Search only in "/etc/myapp" and "/etc/fallback"
        >>> effective_path(config_id, search_path="/etc/myapp:/etc/fallback")

        >>> # Add "/etc/myapp" to the paths defined by XDG
        >>> assert os.environ["FOO_BAR_PATH"] == "+/etc/myapp"
        >>> effective_path(ConfigId("foo", "bar"))
    """
    log, _ = prefixed_logger(config_id)

    # default search path
    path = (
        [f"/etc/{config_id.group}/{config_id.app}"]
        + get_xdg_dirs(config_id)
        + [
            get_xdg_home(config_id),
            join(getcwd(), f".{config_id.group}", config_id.app),
        ]
    )

    # If a path was passed directly to this instance, override the path.
    if search_path:
        path = search_path.split(pathsep)

    # Next, consider the environment variables...
    env_path_name = "{}_{}_PATH".format(
        config_id.group.upper(), config_id.app.upper()
    )
    env_path = getenv(env_path_name)

    if env_path and env_path.startswith("+"):
        # If prefixed with a '+', append the path elements
        additional_paths = env_path[1:].split(pathsep)
        log.info(
            "Search path extended with %r by the environment " "variable %s.",
            env_path,
            env_path_name,
        )
        path.extend(additional_paths)
    elif env_path:
        # Otherwise, override again. This takes absolute precedence.
        log.info(
            "Configuration search path was overridden with "
            "%r by the environment variable %r.",
            env_path,
            env_path_name,
        )
        path = env_path.split(pathsep)

    return path


def find_files(
    config_id: ConfigID,
    search_path: Optional[List[str]] = None,
    filename: str = "",
) -> Generator[str, None, None]:
    """
    Looks for files in default locations. Returns an iterator of filenames.

    :param config_id: A "ConfigID" object used to identify the config folder.
    :param search_path: A list of paths to search for files.
    :param filename: The name of the file we search for.
    """
    search_path_ = search_path or []
    config_filename = effective_filename(config_id, filename)

    # Next, use the resolved path to find the filenames. Keep track of
    # which files we loaded in order to inform the user.
    for dirname in search_path_:
        conf_name = join(dirname, config_filename)
        yield conf_name


def effective_filename(config_id: ConfigID, config_filename: str) -> str:
    """
    Returns the filename which is effectively used by the application. If
    overridden by an environment variable, it will return that filename.

    *config_id* is used to determine the name of the variable. If that does not
    return a value, *config_filename* will be returned instead.
    """
    log, _ = prefixed_logger(config_id)

    env_filename = getenv(env_name(config_id))
    if env_filename:
        log.info(
            "Configuration filename was overridden with %r "
            "by the environment variable %s.",
            env_filename,
            env_name(config_id),
        )
        config_filename = env_filename

    return config_filename


def env_name(config_id: ConfigID) -> str:
    """
    Return the name of the environment variable which contains the file-name to
    load.
    """
    return f"{config_id.group.upper()}_{config_id.app.upper()}_FILENAME"


def is_readable(
    config_id: ConfigID,
    filename: str,
    version: Optional[Version] = None,
    secure: bool = False,
    handler: "Optional[Type[Handler[Any]]]" = None,
) -> FileReadability:
    """
    Check if ``filename`` can be read. Will return boolean which is True if
    the file can be read, False otherwise.

    :param filename: The exact filename which should be checked.
    :param version: The expected version, that should be found in the file.
    :param secure: Whether we should avoid loading insecure files or not.
    :param handler: The handler to be used to open and parse the file.
    """
    log, _ = prefixed_logger(config_id)
    handler_ = handler or IniHandler  # type: Type[Handler[Any]]

    if not exists(filename):
        return FileReadability(False, filename, "File not found", None)
    log.debug("Checking if %s is readable.", filename)

    insecure_readable = True
    unreadable_reason = "<unknown>"

    # Check if the file is version-compatible with this instance.
    try:
        config_instance = handler_.from_filename(filename)
    except:  #  pylint: disable=bare-except
        log.critical("Unable to read %r", abspath(filename), exc_info=True)
        return FileReadability(
            False,
            filename,
            "Exception encountered when loading the file",
            None,
        )

    instance_version = handler_.get_version(config_instance)

    if version and not instance_version:
        # version is set, so we MUST have a version in the file!
        raise NoVersionError(
            "The config option 'meta.version' is missing in {}. The "
            "application expects version {}!".format(filename, version)
        )

    if version and instance_version:
        # The user expected a certain version. We need to check the version in
        # the file and compare.
        major = instance_version.major
        minor = instance_version.minor
        expected_major = version.major
        expected_minor = version.minor
        if expected_major != major:
            msg = "Invalid major version number in %r. Expected %r, got %r!"
            log.error(msg, abspath(filename), str(version), instance_version)
            insecure_readable = False
            unreadable_reason = msg
        elif expected_minor > minor:
            msg = "Mismatching minor version number in %r. Expected %r, got %r!"
            log.warning(msg, abspath(filename), str(version), instance_version)
            insecure_readable = False
            unreadable_reason = msg

    if insecure_readable and secure:
        if _is_world_readable(filename):
            msg = "File %r is not secure enough. Change it's mode to 600"
            log.warning(msg, filename)
            return FileReadability(False, filename, msg, instance_version)
    return FileReadability(
        insecure_readable, filename, unreadable_reason, instance_version
    )
