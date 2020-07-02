Changelog
=========

Release 5.0.0
-------------

.. warning::

    Major API changes! Read the full documentation before upgrading!

* Python 2 support is now dropped!
* Add the possibility to supply a custom file "handler" (f.ex. YAML or other
  custom parsers).
* Add :py:mod:`config_resolver.handler.json` as optional file-handler.
* Refactored from a simple module to a full-fledged Python package
* Retrieving a config instance no longer returns a subclass of the
  :py:class:`configparser.ConfigParser` class. Instead, it will return whatever
  the supplied handler creates.
* External API changed to a functional API. You no longer call the ``Config``
  constructor, but instead use the :py:func:`~config_resolver.get_config()`
  function. See the API docs for the changes in function signature.
* Retrieval meta-data is returned along-side the retrieved config. This
  separation allows a custom handler to return any type without impacting the
  internal logic of ``config_resolver``.
* Dropped the deprectaed lookup in ``~/.group-name/app-name`` in favor of the
  XDG standard ``~/.config/group-name/app-name``.
* Fully type-hinted
* Slightly less aggressive logging (as of 5.0.1 by Vince Broz)

Upgrading from 4.x
~~~~~~~~~~~~~~~~~~

* Replace ``Config`` with ``get_config``
* The result from the call to ``get_config`` now returns a named-tuple with two
  objects: The config instance (``.config``) and additional metadata
  (``.meta``).
* The following attributes moved to the meta-data object:

  * ``active_path``
  * ``prefix_filter``
  * ``loaded_files``

* Return types for INI files is now a standard library instance of
  :py:class:`configparser.ConfigParser`. This means that the ``default``
  keyword argument to ``get`` has been replaced with ``fallback``.

Release 4.3.8
-------------

Fixed
~~~~~

* Fixed a regression introduced in 4.3.7 which caused log-files no longer to be
  loaded if ``meta.version`` had a mismatching minor-version


.. note::

   While it may make sense to refuse loading config-version 1.2 when the app
   asks for 1.4 (larger minor-version, same major-version), this would
   introduce a backwards incompatibility and will break some apps using this.

   This fix reverts that change from 4.3.7 but keeps the change on the test
   deciding whether to log a warning or not, Before 4.3.7 we always emitted a
   warning whenever the minor-version was *different*. Now we only emit one
   when the minor version is too low in the loaded config-file.


Release 4.3.7
-------------

Fixed
~~~~~

* Fix changelog in generated docs
* Don't log a warning when loading a config-file with a compatible (but
  different) version.


Release 4.3.6
-------------

Fixed
~~~~~

* If a config-file contains any parser errors, that file is skipped while
  logging a "critical" error. This prevents crashes caused by broken configs.


Release 4.3.5
-------------

Fixed
~~~~~

* The deprecation warning about the *filename* argument stated the exact
  opposite to what it should have said :( This is fixed now


Release 4.3.4
-------------

Fixed
~~~~~

* Don't emit deprecation warnings when the code is called as expected.


Release 4.3.3
-------------

Fixed
~~~~~

* Fixed a regression introduced by 4.3.2


Release 4.3.2
-------------

Fixed
~~~~~

* Replace hand-crafted code with ``stack_level`` information for deprecation
  warnings


Release 4.3.1.post1
-------------------

Fixed
~~~~~

* Fixed type hints
* Arguments ``require_load`` and ``version`` are no longer ignored in
  ``get_config``


Release 4.3.1
-------------

Fixed
~~~~~

* Fixed return-value of ``get_config``. It now properly returns the same return
  value as config-resolver 5. New deprecation warnings have been added as well.

  .. warning::
    This will **BREAK** your code as ``get_config`` now returns a tuple, with
    the config instance being the first element! This should never have entered
    like this in the 4.x branch. Sorry about that.

* Fixed missing ``NoSectionError`` and ``NoOptionError`` imports (regression
  from ``4.2.5`` via commit ``54168cd``)


Release 4.3.0
-------------

Added
~~~~~

* The new "transition" function ``get_config`` now also honors the
  ``secure`` flag in ``lookup_options``.


Release 4.2.5.post2
-------------------

Fixes
~~~~~

* ``filename`` can now be passed as direct argument to ``get_config``
* Don't warn if the config is retrieved correctly


Release 4.2.5.post1
-------------------

Fixes
~~~~~

* Improved warning detail in deprecation messages.


Release 4.2.5
-------------

Fixes
~~~~~

* Change from a module-only distrbution to a package (for PEP-561)
* Make package PEP-561 compliant
* Add transition function ``config_resolver.get_config`` for a smoother upgrade
  to v5.0 in the future.
* Add deprecation warnings with details on how to change the code for a smooth
  transition to v5.0


Release 4.2.4
-------------

Fixes
~~~~~

* Improve code quality.
* Improve log message for invalid config version numbers.


Release 4.2.3
-------------

Fixes
~~~~~

* Unit tests fixed
* Added missing LICENSE file
* Log messages will now show the complete version string
* Auto-detect version number if none is specifiec in the ``[meta]`` section.
* Fix travis CI pipeline


Release 4.2.2
-------------

Fixes
~~~~~

* Python 2/3 class-inheritance fixed.


Release 4.2.1
-------------

Fixes
~~~~~

* Log message prefixes no longer added multiple times


Release 4.2.0
-------------

Features added
~~~~~~~~~~~~~~

* GROUP and APP names are now included in the log messages.

Release 4.1.0
-------------

Features added
~~~~~~~~~~~~~~

* XDG Basedir support

  ``config_resolver`` will now search in the folders/names defined in the :ref:`XDG
  specification <xdg-spec>`.

Release 4.0.0
-------------

Features added
~~~~~~~~~~~~~~

* Config versioning support.

  The config files can now have a section ``meta`` with the key ``version``.
  The version is specified in dotted-notation with a major and minor number
  (f.ex.: ``version=2.1``). Configuration instances take an optional
  ``version`` argument as well. If specified, config_resolver expects the
  ``meta.version`` to be there. It will raise a
  ``config_resolver.NoVersionError`` otherwise. Increments in the major number
  signify an incompatible change. If the application expectes a different major
  number than stored in the config file, it will raise a
  ``config_resolver.IncompatibleVersion`` exception. Differences in minor
  numbers are only logged.

Improvments
~~~~~~~~~~~

* The ``mandatory`` argument **has been dropped**! It is now implicitly assumed
  it the ``.get`` method does not specify a default value. Even though
  "explicit is better than implicit", this better reflects the behaviour of the
  core ``ConfigParser`` and is more intuitive.

* Legacy support of old environment variable names **has been dropped**!

* Python 3 support.

* When searching for a file on the current working directory, look for
  ``./.group/app/app.ini`` instead of simply ``./app.ini``. This solves a
  conflict when two modules use config_resolver in the same application.

* Better logging.


Release 3.3.0
-------------

Features added
~~~~~~~~~~~~~~

* New (optional) argument: ``require_load``. If set to ``True`` creating a
  config instance will raise an error if no appropriate config file is found.

* New class: ``SecuredConfig``: This class will refuse to load config files
  which are readable by other users than the owner.

Improvments
~~~~~~~~~~~~~~~~~

* Documentation updated/extended.
* Code cleanup.

Release 3.2.2
-------------

Improvments
~~~~~~~~~~~~~~~~~

* Unit tests added

Release 3.2.1
-------------

Fixes/Improvments
~~~~~~~~~~~~~~~~~

* The "group" name has been prefixed to the names of the environment variables.
  So, instead of APP_PATH, you can now use GROUP_APP_PATH instead. Not using
  the GROUP prefix will still work but emit a DeprecationWarning.

Release 3.2
-----------

Features added
~~~~~~~~~~~~~~

* The call to ``get`` can now take an optional default value. More details can
  be found in the docstring.


Release 3.1
-----------

Features added
~~~~~~~~~~~~~~

* It is now possible to extend the search path by prefixing the
  ``<APP_NAME>_PATH`` variable value with a ``+``

* Changelog added


.. vim: set ft=rst :
