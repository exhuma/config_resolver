A system to resolve config files for python projects
====================================================


.. note::

    This is a small piece of code which I ended up copy/pasting over and over
    from project to project. I decided to refactor it out into a separate
    project to facilitate updates. It's something I use for myself. If you
    find it useful for yourself, feel free to use it!


A very simple and small utility to provide a way to search for configuration
files. For now it is only tested on posix systems, but it should also work on
Windows.

For posix systems it will search for config files in the following order:

- A file named in the environment variable ``<APP_NAME>_CONFIG``
- The current active working directory (of the running process)
- ``~/.<group_name>/<app_name>/<conf_name>``
- ``/etc/<group_name>/<app_name>/<conf_name>``

The complete search path can be overwritten by setting the environment variable
``<APP_NAME>_PATH``, separating the different paths by either ``:`` (posix) or
``;`` (windows).
