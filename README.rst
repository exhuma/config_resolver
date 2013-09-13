A system to resolve config files for python projects
====================================================

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


Changelog
=========

.. include:: CHANGES
