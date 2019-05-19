config_resolver
===============

.. image:: https://travis-ci.org/exhuma/config_resolver.svg?branch=master
    :target: https://travis-ci.org/exhuma/config_resolver

Full Documentation
    https://config-resolver.readthedocs.org/en/latest/

Repository
    https://github.com/exhuma/config_resolver

PyPI
    https://pypi.python.org/pypi/config_resolver


Rationale
~~~~~~~~~

Many of the larger frameworks (not only web frameworks) offer their own
configuration management. But it looks different everywhere. Both in code and
in usage later on. Additionally, the operating system usually has some default,
predictable place to look for configuration values. On Linux, this is ``/etc``
and the `XDG Base Dir Spec
<https://standards.freedesktop.org/basedir-spec/0.8/>`_ (This instance is based
on 0.8 of this spec).

The code for finding these config files is always the same. But finding config
files can be more interesting than that:

* If config files contain passwords, the application should issue appropriate
  warnings if it encounters an insecure file and refuse to load it.

* The expected structure in the config file can be versioned (think: schema).
  If an application is upgraded and expects new values to exist in an old
  version file, it should notify the user.

* It should be possible to override the configuration per installed instance,
  even per execution.

``config_resolver`` tackles all these challenges in a simple-to-use drop-in
module. The module uses no additional external modules (no additional
dependencies, pure Python) so it can be used in any application without adding
unnecessary bloat.
