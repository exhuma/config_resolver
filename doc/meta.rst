.. _the-meta-object:

The Meta Object
===============

The return value of :py:func:`~config_resolver.core.get_config` returns a
named-tuple which not only contains the parsed config instance, but also some
additional meta-data.

Before version 5.0 this information was melded into the returned config instance.

The reason this was split this way in version 5.0, is because with this
version, the return type is defined by :py:ref:`the handlers <custom-handler>`.
Now, handlers may have return-types which cannot easily get additional values
grafted onto them (at least not explicitly). To keep it *clear and
understandable*, the values are now *explicitly* returned separately! This give
the handler total freedom of which data-type they work with, and still retain
useful meta-data for the end-user.

The meta-object is accessible via the second return value from
:py:func:`~config_resolver.core.get_config`::

    _, meta = get_config('foo', 'bar')

Or via the ``meta`` attribute on the returned named-tuple::

    result = get_config('foo', 'bar')
    meta = result.meta

At the time of this writing, the meta-object contains the following attributes:

active_path
    A list of path names were used to look for files (in order of the lookup)

loaded_files
    A list of filenames which have been loaded (in order of loading)

config_id
    The internal ID used to identify the application for which the config was
    requested. This corresponds to the first and second argument to
    ``get_config``.

prefix_filter
    A reference to the logging-filter which was added to prefix log-lines with
    the config ID. This exists so a user can easily get a handle on this in
    case it needs to be removed from the filters.
