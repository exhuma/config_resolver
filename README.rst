config_resolver
===============

.. warning::

   **config_resolver is no longer maintained.**
   Version 5.2.0 is the final release:
   there will be no further bug fixes or security updates.

   It cannot override single values from environment variables,
   returns every value as an untyped string,
   returns an empty config instead of an error when no file is found,
   and reads only INI and JSON.
   Its ``secure`` option rejects the group- or world-readable secret
   files that Docker and Kubernetes mount.
   Maintained libraries cover all of this,
   and the XDG lookup fits into a short function.

   `Alternatives and migration
   <https://exhuma.github.io/config_resolver/migration.html>`_
   shows tested replacements for each use case.


Full Documentation
    https://exhuma.github.io/config_resolver/

Repository
    https://github.com/exhuma/config_resolver

PyPI
    https://pypi.python.org/pypi/config_resolver


``config_resolver`` provides a simple, yet flexible way to provide
configuration to your applications. It follows the `XDG Base Dir Spec
<https://standards.freedesktop.org/basedir-spec/0.8/>`_ (This instance is
based on 0.8 of this spec) for config file locations, and adds additional ways
to override config locations. The aims of this package are:

* Provide a simple API
* Follow well-known standards for config-file locations
* Be as close to pure-Python as possible
* Be framework agnostic
* Allow custom configutaion types (``.ini`` and ``.json`` support is shipped by
  default)
* Allow to provide system-wide defaults but allow overriding of values for more
  specific environments. These are (in increasing order of specificity):

  1. System-wide configuration (potentially requiring root-access to modify)
  2. User-level configuration (for all instances running as that user)
  3. Current Working Directory configuration (for a running instance)
  4. Per-Instance configuration
