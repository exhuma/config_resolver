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

* Application & Group name is added to log records

Fixes
~~~~~

* Python 2/3 Unicode fix in log records


Release 4.1.0
-------------

Features added
~~~~~~~~~~~~~~

* XDG Basedir support

  ``config_resolver`` will now search in the folders/names defined in the `XDG
  specification`_.


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
