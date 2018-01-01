Glossary
========

.. glossary::

    file-handler
        A file-handler is a module or class offering a minimal set of functions
        to load files as config files. They can optionally be supplied to
        :py:func:`~config_resolver.core.get_config`. By default, handlers for
        INI and JSON files are supplied. Look at :ref:`custom-handler` for
        details on how to create a new one.
