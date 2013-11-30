Welcome to config_resolver's documentation!
===========================================

Changelog
~~~~~~~~~

.. toctree::
   :maxdepth: 1

   changelog

API
~~~

.. toctree::
   :maxdepth: 1

   api

.. include:: ../README.rst

Description / Usage
~~~~~~~~~~~~~~~~~~~

The module provides two main classes:

* :py:class:`~config_resolver.Config`: This is the default class.
* :py:class:`~config_resolver.SecuredConfig`: This is a subclass of
  :py:class:`~config_resolver.Config` which refuses to load files which a
  readable by other people than the owner.

The simple usage for both is identical. The only difference is the above
mentioned decision to load files or not::

    from config_resolver imoprt Config
    cfg = Config('acmecorp', 'bird_feeder')

This will look for config files in (in that order):

* ``/etc/acmecorp/bird_feeder/app.ini``
* ``/etc/xdg/acmecorp/bird_feeder/app.ini``
* ``~/.acmecorp/bird_feeder/app.ini`` -- This will be deprecated (no longer
  loaded) in ``config_resolver 5.0``
* ``~/.config/acmecorp/bird_feeder/app.ini``
* ``./.acmecorp/bird_feeder/app.ini``

If all files exist, one which is loaded later, will override the values of an
earlier file. No values will be removed, this means you can put system-wide
defaults in ``/etc`` and specialise/override from there.

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

.. tip:: If a config file is found at ``~/.<group>/<app>``, a log message with
         a warning is issued since config_resolver 4.1.0 encouraging the
         end-user to move the config file to ``~/.config/<group>/<app>``.

Files are parsed using the default Python :py:class:`configparser.ConfigParser`
(i.e. ``ini`` files).

Advanced Usage
~~~~~~~~~~~~~~

Versioning
----------

It is pretty much always useful to keep track of the expected "schema" of a
config file. If in a later version of your application, you decide to change a
configuration value's name, remove a variable, or require a new one the
end-user needs to be notified.

For this use-case, you can create versioned :py:class:`config_resolver.Config`
instances in your application::

    cfg = Config('group', 'app', version='2.1')

Config file example::

    [meta]
    version=2.1

    [database]
    dsn=foobar

If you don't specify a version number in the construcor, an unversioned file is
assumed.

Only "major" and "minor" numbers are supported. If the application encounters a
file with a different "major" value, it will raise a
:py:class:`config_resolver.IncompatibleVersion` exception. Differences in minor
numbers are only logged with a "warning" level.

Rule of thumb: If your application accepts a new config value, but can function
just fine with default values, increment the minor number. If on the other
hand, something has changed, and the user needs to change the config file,
increment the major number.

Requiring files (bail out if no config is found)
------------------------------------------------

Since version 3.3.0, you have a bit more control about how files are loaded.
The :py:class:`config_resolver.Config` class takes a new argument:
``require_load``. If this is set to ``True``, an :py:exc:`OSError` is raised
if no config file was loaded. Alternatively, and, purely a matter of taste, you
can leave this on it's default ``False`` value and inspect the ``loaded_files``
attribute on the :py:class:`config_resolver.Config` instance. If it's empty,
nothing has been loaded.

Overriding internal defaults
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both the search path and the basename of the file (``app.ini``) can be
overridden by the application developer via the API and by the end-user via
environment variables.

By the application developer
----------------------------

Apart from the "group name" and "application name", the
:py:class:`config_resolver.Config` class accepts ``search_path`` and
``filename`` as arguments. ``search_path`` controls to what folders are
searched for config files, ``filename`` controls the basename of the config
file. ``filename`` is especially useful if you want to separate different
concepts into different files::

    app_cfg = Config('acmecorp', 'bird_feeder')
    db_cfg = Config('acmecorp', 'bird_feeder', filename='db.ini')

By the end-user
---------------

The end-user has access to two environment variables:

* ``<GROUP_NAME>_<APP_NAME>_PATH`` overrides the default search path.
* ``XDG_CONFIG_HOME`` overrides the path considered as "home" locations for
  config files (default=``~/.config``)
* ``XDG_CONFIG_DIRS`` overrides additional path elements as recommended by
  `the freedesktop.org XDG basedir spec`_. Paths are separated by ``:`` and are
  sorted with descending precedence (leftmost is the most important one).
* ``<GROUP_NAME>_<APP_NAME>_FILENAME`` overrides the default basename of the
  config file (default=``app.ini``).


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
    conf = Config('mycompany', 'myapplication')

If you want to use the ``INFO`` level in your application, but silence only the
config_resolver logs, add the following to your code::

    logging.getLogger('config_resolver').setLevel(logging.WARNING)

As of version 4.2.0, all log messages are prefixed with the group and
application name. This helps identifying log messages if multiple packages in
your application use ``config_resolver``. The prefix filter can be accessed via
the instance member ``_prefix_filter`` if you want to change or remove it::

    from config_resolver import Config
    conf = Config('mycompany', 'myapplication')
    print conf._prefix_filter

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


Difference to ConfigParser
~~~~~~~~~~~~~~~~~~~~~~~~~~

There is one **major** difference to the default Python
:py:class:`~configparser.ConfigParser`: the
:py:meth:`~config_resolver.Config.get` method accepts a "default" parameter. If
specified, that value is returned in case
:py:class:`~configparser.ConfigParser` does not return a value. Remember that
the ``ConfigParser`` instance supports defaults as well if specified in the
constructor.

Using the ``default`` parameter on :py:meth:`~config_resolver.Config.get`, you
can now have two options with the same name in two sections with *different*
values.  Imagine the following::

    [database1]
    dsn=sqlite:///tmp/db.sqlite3

    [database2]
    dsn=sqlite:///tmp/db2.sqlite3

In the core :py:class:`~configparser.ConfigParser` you could *not* specify two
different default values! The ``default`` parameter makes this possible.

.. note::
    *AGAIN:* The core :py:class:`~configparser.ConfigParser` default mechanism
    still takes precedence!

Debugging
---------

Creating an instance of :py:class:`~config_resolver.Config` will not raise an
error (except if explicitly asked to do so).  Instead it will always return a
valid, (but possibly empty) instance. So errors can be hard to see sometimes.

The idea behind this, is to encourage you to have sensible default values, so
that the application can run, even without configuration. For
"development-time" exceptions, consider calling
:py:meth:`~config_resolver.Config.get` without a default value.

Your first stop should be to configure logging and look at the emitted
messages.

In order to determine whether any config file was loaded, you can look into the
``loaded_files`` instance variable. It contains a list of all the loaded files,
in the order of loading.  If that list is empty, no config has been found. Also
remember that the order is important. Later elements will override values from
earlier elements.

Additionally, another instance variable named ``active_path`` represents the
search path after processing of environment variables and runtime parameters.
This may also be useful to display informtation to the end-user.


Examples
========

A simple config instance (with logging)::

    import logging
    from config_resolver import Config

    logging.basicConfig(level=logging.DEBUG)
    cfg = Config("acmecorp", "bird_feeder")
    print cfg.get('section', 'var')

An instance which will not load unsecured files::

    import logging
    from config_resolver import SecuredConfig

    logging.basicConfig(level=logging.DEBUG)
    cfg = SecuredConfig("acmecorp", "bird_feeder")
    print cfg.get('section', 'var')

Loading a versioned config file::

    import logging
    from config_resolver import Config

    logging.basicConfig(level=logging.DEBUG)
    cfg = Config("acmecorp", "bird_feeder", version="1.0")
    print cfg.get('section', 'var')

Default values::

    import logging
    from config_resolver import Config

    logging.basicConfig(level=logging.DEBUG)
    cfg = Config("acmecorp", "bird_feeder", version="1.0")

    # This will not raise an error (but emit a DEBUG log entry).
    print cfg.get('section', 'example_non_existing_option_name', default=10)

    # this may raise a "NoOptionError"
    print cfg.get('section', 'example_non_existing_option_name')

    # this may raise a "NoSectionError"
    print cfg.get('example_non_existing_section_name', 'varname')


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _freedesktop.org: http://www.freedesktop.org
.. _the freedesktop.org XDG basedir spec:
.. _XDG specification: http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
.. _logging tutorial: http://docs.python.org/3.2/howto/logging.html#logging-basic-tutorial
