Usage
#####

Basics
~~~~~~

The module provides one function to retrieve a config instance:

* :py:func:`~config_resolver.core.get_config`

and one function to create a config from a text-string:

* :py:func:`~config_resolver.core.from_string`

A simple usage looks like this::

    from config_resolver import get_config
    result = get_config('bird_feeder', 'acmecorp')
    cfg = result.config  # The config instance (its type depends on the handler)
    meta = result.meta  # Metadata for the loading-process

This will look for config files in (in that order):

* ``/etc/acmecorp/bird_feeder/app.ini``
* ``/etc/xdg/acmecorp/bird_feeder/app.ini``
* ``~/.config/acmecorp/bird_feeder/app.ini``
* ``./.acmecorp/bird_feeder/app.ini``

If all files exist, one which is loaded later, will override the values of an
earlier file. No values will be removed, this means you can put system-wide
defaults in ``/etc`` and specialise/override from there.

.. note::

    The above is true for the file handlers included with
    :py:mod:`config_resolver`.  Since version 5.0 it is possible to provide
    custom file-handlers, which may behave differently. If using a custom
    file-handler make sure to understand how it behaves! See
    :ref:`custom-handler`.

.. _xdg-spec:

The Freedesktop XDG standard
----------------------------

`freedesktop.org`_ standardises the location of configuration files in the `XDG
specification`_ Since version 4.1.0, ``config_resolver`` reads these paths as
well, and honors the defined environment variables. To ensure backwards
compatibility, those paths have only been added to the resolution order. They
have a higher precedence than the old locations though. So the following
applies:

============================== =======================
XDG item                        overrides
============================== =======================
``/etc/xdg/<group>/<app>``      ``/etc/<group>/<app>``
``~/.config/<group>/</app>``    ``~/.<group>/<app>``
``$XDG_DATA_HOME``              ``$GROUP_APP_PATH``
``$XDG_CONFIG_DIRS``            ``$GROUP_APP_PATH``
============================== =======================

By default, files are parsed using the default Python
:py:class:`configparser.ConfigParser` (i.e. ``ini`` files). Custom file
"handlers" may read other formats. See :ref:`custom-handler`.

Advanced Usage
~~~~~~~~~~~~~~

The way config_resolver finds files can be controlled by an optional
``lookup_options`` argument to :py:func:`~config_resolver.core.get_config`.
This is a dictionary controlling how the files are searched and which files are
valid.  The default options are::

    default_options = {
        'search_path': '',  # <- empty string here triggers the default search path
        'filename': 'app.ini',  # <- this depends on the file-handler
        'require_load': False,
        'version': None,
        'secure': False,
    }

All values in the dictionary are optional. Not all values have to be supplied.
Missing values will use the default value shown above.

Versioning
----------

It is pretty much always useful to keep track of the expected "schema" of a
config file. If in a later version of your application, you decide to change a
configuration value's name, remove a variable, or require a new one the
end-user needs to be notified.

For this use-case, you can use the lookup option ``version`` to allow only
files of the proper version to be loaded. If the version differs in a detected
file, a log message will be emitted::

    result = get_config('group', 'app', {'version': '2.1'})

Config file example::

    [meta]
    version=2.1

    [database]
    dsn=foobar

If you don't specify a version number in the constructor versioning will
trigger automatically on the first file encountered which has a version number.
The reason this triggers is to prevent accidentally loading files further down
the chain which have an incompatible version.

Only "major" and "minor" numbers are supported. If the application encounters a
file with a different "major" value, it will emit a log message with severity
``ERROR`` and the file will be skipped. If the minor version of a file is
smaller than the expected version, an error is logged as well and the file is
skipped. If the minor version is equal or larger (inside the config file), then
the file will be loaded.

In other words, for a file to be loaded, the major versions that the
application expected (via the ``get_config`` call) must match the major version
in the config-file **and** the expectes minor version must be **smaller** than
the minor version inside the config-file.


Requiring files (bail out if no config is found)
------------------------------------------------

Since version 3.3.0, you have a bit more control about how files are loaded.
The :py:func:`~config_resolver.core.get_config` function takes the
lookup_options value ``require_load``. If this is set to ``True``, an
:py:exc:`OSError` is raised if no config file was loaded. Alternatively, and,
purely a matter of presonal preference, you can leave this on it's default
``False`` value and inspect the ``loaded_files`` attribute on the ``meta``
attribute of the returned result. If it's empty, nothing has been loaded.

Overriding internal defaults
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both the search path and the basename of the file (``app.ini``) can be
overridden by the application developer via the API and by the end-user via
environment variables.

By the application developer
----------------------------

Apart from the "group name" and "application name", the
:py:func:`~config_resolver.core.get_config` function accepts ``search_path``
and ``filename`` as values in ``lookup_options``. ``search_path`` controls to
what folders are searched for config files, ``filename`` controls the basename
of the config file. ``filename`` is especially useful if you want to separate
different concepts into different files::

    app_cfg = get_config('acmecorp', 'bird_feeder').config
    db_cfg = get_config('acmecorp', 'bird_feeder', {'filename': 'db.ini'})

By the end-user
---------------

The end-user has access to two environment variables:

* ``<GROUP_NAME>_<APP_NAME>_PATH`` overrides the default search path.
* ``XDG_CONFIG_HOME`` overrides the path considered as "home" locations for
  config files (default = ``~/.config``)
* ``XDG_CONFIG_DIRS`` overrides additional path elements as recommended by
  `the freedesktop.org XDG basedir spec`_. Paths are separated by ``:`` and are
  sorted with descending precedence (leftmost is the most important one).
* ``<GROUP_NAME>_<APP_NAME>_FILENAME`` overrides the default basename of the
  config file (default = ``app.ini``).


Logging
~~~~~~~

All operations are logged using the default :py:mod:`logging` package with a
logger with the name ``config_resolver``. All operational logs (opening/reading
file) are logged with the ``INFO`` level. The log messages include the absolute
names of the loaded files. If a file is not loadable, a ``WARNING`` message is
emitted. It also contains a couple of ``DEBUG`` messages. If you want to see
those messages on-screen you could do the following::

    import logging
    from config_resolver import Config
    logging.basicConfig(level=logging.DEBUG)
    conf = get_config('mycompany', 'myapplication').config

If you want to use the ``INFO`` level in your application, but silence only the
config_resolver logs, add the following to your code::

    logging.getLogger('config_resolver').setLevel(logging.WARNING)

As of version 4.2.0, all log messages are prefixed with the group and
application name. This helps identifying log messages if multiple packages in
your application use ``config_resolver``. The prefix filter can be accessed via
the "meta" member ``prefix_filter`` if you want to change or remove it::

    from config_resolver import Config
    conf = get_config('mycompany', 'myapplication')
    print(conf.meta.prefix_filter)

More detailed information about logging is out of the scope of this document.
Consider reading the `logging tutorial`_ of the official Python docs.

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

The resolver can also be manipulated using environment variables to allow
different values for different running instances. The variable names are all
upper-case and are prefixed with both group- and application-name.

``<group_name>_<app_name>_PATH``
    The search path for config files. You can specify multiple paths by
    separating it by the system's path separator default (``:`` on Linux).

    If the path is prefixed with ``+``, then the path elements are *appended*
    to the default search path.

``<group_name>_<app_name>_FILENAME``
    The file name of the config file. Note that this should *not* be given with
    leading path elements. It should simply be a file basename (f.ex.:
    ``my_config.ini``)

``XDG_CONFIG_HOME`` and ``XDG_CONFIG_DIRS``
    See the `XDG specification`_


Debugging
---------

Calling :py:func:`~config_resolver.core.get_config` will not raise an error
(except if explicitly asked to do so).  Instead it will always return a valid,
(but possibly empty) instance. So errors can be hard to see sometimes.

The idea behind this, is to encourage you to have sensible default values, so
that the application can run, even without configuration.

Your first stop should be to configure logging and look at the emitted
messages.

In order to determine whether any config file was loaded, you can look into the
``loaded_files`` "meta" variable. It contains a list of all the loaded files,
in the order of loading.  If that list is empty, no config has been found. Also
remember that the order is important. Later elements will override values from
earlier elements (depending of the used ``handler``).

Additionally, another "meta" variable named ``active_path`` represents the
search path after processing of environment variables and runtime parameters.
This may also be useful to display information to the end-user.


Examples
========

A simple config instance (with logging):

.. literalinclude:: examples/example01.py
   :language: python

An instance which will not load unsecured files:

.. literalinclude:: examples/example02.py
   :language: python

Loading a versioned config file:

.. literalinclude:: examples/example03.py
   :language: python

Inspect the "meta" variables:

.. literalinclude:: examples/example04.py
   :language: python


.. _freedesktop.org: http://www.freedesktop.org
.. _the freedesktop.org XDG basedir spec:
.. _XDG specification: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
.. _logging tutorial: http://docs.python.org/3.2/howto/logging.html#logging-basic-tutorial
