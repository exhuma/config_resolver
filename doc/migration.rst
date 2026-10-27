Alternatives and migration
==========================

``config_resolver`` is no longer maintained.
Version 5.2.0 is the final release.
This page shows how to cover its common use cases
with maintained libraries or the standard library.
Every snippet below runs in the project's test suite
(``tests/test_migration_snippets.py``).

Pick the section that matches the application:

* A service in a container: `Containerised services`_.
* Existing INI files, smallest change: `Keep the INI files`_.
* A tool installed on a host, with system and user files:
  `Command-line tools with an XDG cascade`_.

The last two sections replace the ``version`` and ``secure`` lookup
options.


Silence the warning while migrating
-----------------------------------

Version 5.2.0 emits
:py:class:`~config_resolver.exc.ConfigResolverDeprecationWarning`
on every call to :py:func:`~config_resolver.core.get_config` and
:py:func:`~config_resolver.core.from_string`.
It is a :py:class:`DeprecationWarning`, so Python hides it by default
outside ``__main__`` and test runners.
Code that runs with ``-W error`` fails on these calls.
To silence only this warning until the migration is done:

.. code-block:: python

   import warnings

   from config_resolver import (
       ConfigResolverDeprecationWarning,
   )

   warnings.filterwarnings(
       "ignore",
       category=ConfigResolverDeprecationWarning,
   )

In pytest, add this to the ``filterwarnings`` setting:

.. code-block:: ini

   ignore::config_resolver.ConfigResolverDeprecationWarning


Containerised services
----------------------

A service in a container takes its configuration from environment
variables and mounted secret files (`twelve-factor app, factor III
<https://12factor.net/config>`_).
`pydantic-settings <https://docs.pydantic.dev/latest/concepts/pydantic_settings/>`_
does this and checks every value against a type:

.. literalinclude:: migration/service_settings.py
   :language: python

* ``MYAPP_DEBUG=true`` sets ``debug``.
  ``MYAPP_DATABASE__HOST=db`` sets ``database.host``:
  ``__`` separates nested fields.
* ``db_password`` comes from the file ``/run/secrets/myapp_db_password``
  when no ``MYAPP_DB_PASSWORD`` variable is set.
  Secret files carry the same prefix as the variables.
* :py:class:`~pydantic.SecretStr` keeps the password out of
  ``repr()`` and logs; call ``get_secret_value()`` to use it.
* A missing or invalid value stops the program at start-up with a
  message that names the field.
  ``config_resolver`` returned an empty config instead.


Keep the INI files
------------------

To keep the existing files and change as little as possible, use
:py:class:`configparser.ConfigParser` from the standard library on the
same paths ``config_resolver`` searched:

.. literalinclude:: migration/ini_files.py
   :language: python

:py:meth:`~configparser.ConfigParser.read` already does what
``config_resolver`` did with its default INI handler:

* it skips files that do not exist;
* it applies the others in order, so later files override earlier
  ones;
* it returns the list of files it read, the same list as
  ``meta.loaded_files``.

The empty-list check makes a missing config an error;
remove it to keep the old behaviour.
``config_resolver`` also honoured ``<GROUP>_<APP>_PATH`` and
``<GROUP>_<APP>_FILENAME``; if deployments set them, read them with
:py:data:`os.environ` in ``config_paths()``.


Command-line tools with an XDG cascade
--------------------------------------

A tool installed on a host often has system-wide defaults, a user file
that overrides them, and a ``--config`` option or an environment
variable that names one more file.
`platformdirs <https://platformdirs.readthedocs.io/>`_ finds the
directories on every platform, and :py:mod:`tomllib` (Python 3.11 and
later) reads TOML.
On Python 3.10 and earlier, install
`tomli <https://pypi.org/project/tomli/>`_, which has the same API.

.. literalinclude:: migration/cli_config.py
   :language: python

* The files load in this order: each directory in
  ``XDG_CONFIG_DIRS`` (``/etc/xdg`` by default), then
  ``~/.config/bird-feeder/config.toml``, then the file named in
  ``BIRD_FEEDER_CONFIG`` or passed as *explicit*.
* Nested tables merge key by key; later files win.
* ``load_config()`` returns the files it loaded as the second value,
  for a ``--show-config`` option or a log line.
* A file named explicitly must exist; the default locations are
  optional.


Replace the version check
-------------------------

The ``version`` lookup option compared a ``[meta] version`` entry in
each file with the version the application expected.
Instead, give the file a ``schema_version`` field and validate the
whole config with a :py:class:`pydantic.BaseModel`.
A file with another version then fails validation like any other
wrong value:

.. literalinclude:: migration/schema_version.py
   :language: python

``Config.model_validate(config)`` accepts the dictionary returned by
``load_config()`` in the previous section.
``pydantic-settings`` models from the first section validate the same
way.


Replace ``secure=True``
-----------------------

``secure=True`` skipped every file that the group or other users could
read.
It did not check who owned the file, so a file that another user could
replace still passed.
This check looks at both:

.. literalinclude:: migration/private_file.py
   :language: python

Call ``check_private(path)`` before reading a file that holds secrets.
:py:func:`os.getuid` exists on POSIX systems only.

.. note::

   Do not run this check on secrets mounted into a container.
   Docker and Kubernetes usually mount them as ``0444`` or ``0644``,
   owned by root.
   The mount protects them, not the file mode: only the container sees
   the file.


Other options
-------------

`Dynaconf <https://www.dynaconf.com/>`_
   Layered settings from TOML, YAML, JSON, INI, ``.env`` files,
   environment variables and secret stores, with per-environment
   sections.

`environs <https://pypi.org/project/environs/>`_
   Parses and validates environment variables into Python types; reads
   ``.env`` files.

`python-decouple <https://pypi.org/project/python-decouple/>`_
   Reads settings from environment variables with fallbacks to ``.env``
   or ``settings.ini`` files, with simple type casting.
