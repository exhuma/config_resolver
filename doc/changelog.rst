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