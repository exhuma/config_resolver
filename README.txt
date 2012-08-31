A system to resolve config files for python projects
====================================================

A very simple and small utility to provide a way to search for configuration
files. For now it is only tested on posix systems, but it should also work on
Windows.

For posix systems it will search for config files in the following order:

- ``/etc/<group_name>/<app_name>/<conf_name>``
- ``~/.<group_name>/<app_name>/<conf_name>``
- The current active working directory (of the running process)
- A file named in the environment variable ``<APP_NAME>_CONFIG``

The complete search path can be overwritten by setting the environment variable
``<APP_NAME>_PATH``, separating the different paths by either ``:`` (posix) or
``;`` (windows).

The last file found will always take precedence by extending/overwriting
previously loaded files. As an example you can have system globals in
``/etc``, and then on a per-user basis override values. Existing values are
kept, so config files further down the lookup chain do not contain all values.

Even further down the lookup chain you can use the working-directory or
``<APP_NAME>_CONFIG`` to override values on a per-application instance basis.
