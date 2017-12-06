User Manual
===========

.. image:: https://travis-ci.org/exhuma/config_resolver.svg?branch=master
    :target: https://travis-ci.org/exhuma/config_resolver

Fulll Documentation
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
<http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_.

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

One last thing that ``config_resolver`` provides, is a better handling of
default values than instances of ``SafeConfigParser`` of the standard library.
The stdlib config parser can only specify defaults for options without
associating them to a section! This means that you cannot have two options with
the same name in multiple sections with different default values.
``config_resolver`` handles default values at the time you call ``.get()``,
which makes it independent of the section.
