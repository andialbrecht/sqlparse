User Interfaces
===============

``sqlformat``
  The ``sqlformat`` command line script is distributed with the module.
  Run :command:`sqlformat --help` to list available options and for usage
  hints.

Pre-commit Hook
^^^^^^^^^^^^^^^^

``sqlparse`` can be integrated with `pre-commit <https://pre-commit.com/>`_
to automatically format SQL files before committing them to version control.

To use it, add the following to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/andialbrecht/sqlparse
       rev: 0.5.5  # Replace with the version you want to use
       hooks:
         - id: sqlformat

The hook will format your SQL files with basic indentation (``--reindent``) by default.

To customize formatting options, override the ``args`` parameter:

.. code-block:: yaml

   repos:
     - repo: https://github.com/andialbrecht/sqlparse
       rev: 0.5.5
       hooks:
         - id: sqlformat
           args: [--in-place, --reindent, --keywords, upper, --identifiers, lower]

.. important::

   When overriding ``args``, you **must include** ``--in-place``, otherwise
   :command:`sqlformat` writes to stdout and the hook leaves your files
   unchanged.

Common formatting options include:

* ``--in-place``: Required - modify files in-place (always include this)
* ``--reindent`` or ``-r``: Reindent statements
* ``--keywords upper`` or ``-k upper``: Convert keywords to uppercase
* ``--identifiers lower`` or ``-i lower``: Convert identifiers to lowercase
* ``--indent_width 4``: Set indentation width to 4 spaces
* ``--strip-comments``: Remove comments from SQL

Run ``sqlformat --help`` for a complete list of formatting options.

After adding the configuration, install the pre-commit hooks:

.. code-block:: bash

   pre-commit install

The hook will now run automatically before each commit. You can also run
it manually on all files:

.. code-block:: bash

   pre-commit run sqlformat --all-files

``sqlformat.org``
  A web front-end that exposes the formatting features of :mod:`sqlparse`
  online. See https://sqlformat.org/.

