User Manual
===========

Read the full manual at http://config-resolver.readthedocs.org/en/latest/

Rationale
~~~~~~~~~

Configuration values are usually found on well defined locations. On Linux
systems this is usually ``/etc`` or the home folder. The code for finding these
config files is always the same. But finding config files can be more
interesting than that:

* If config files contain passwords, the application should issue appropriate
  warnings if it encounters an insecure file and refuse to load it.

* The expected structure in the config file can be versioned (think: schema).
  If an application is upgraded and expects new values to exist in an old
  version file, it should notify the user.

* It should be possible to override the configuration on a per installed
  instance, even per-execution.

``config_resolver`` tackles all these challenges in a simple-to-use drop-in
module. The module uses no additional external modules (no additional
dependencies, pure Python).

Additionally, the existing "default values" mechanisms in Python is broken, in
that cannot have two different default values for the same variable name in two
different sections.
