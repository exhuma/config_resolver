config_resolver
===============


Full Documentation
    https://config-resolver.readthedocs.org/en/latest/

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
