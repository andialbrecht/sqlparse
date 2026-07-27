Introduction
============


Download & Installation
-----------------------

Install :mod:`sqlparse` from the `Python Package Index (PyPI)
<https://pypi.org/project/sqlparse/>`_ using :command:`pip`:

.. code-block:: bash

   $ pip install sqlparse

:mod:`sqlparse` requires Python 3.10 or later and has no dependencies.


Getting Started
---------------

The :mod:`sqlparse` module provides three simple functions on module level
to achieve some common tasks when working with SQL statements.
This section shows some simple usage examples of these functions.

Let's get started with splitting a string containing one or more SQL
statements into a list of single statements using :meth:`~sqlparse.split`:

.. code-block:: python

  >>> import sqlparse
  >>> sql = 'select * from foo; select * from bar;'
  >>> sqlparse.split(sql)
  ['select * from foo;', 'select * from bar;']

The end of a statement is identified by the occurrence of a semicolon.
Semicolons within certain SQL constructs like ``BEGIN ... END`` blocks
are handled correctly by the splitting mechanism.

SQL statements can be beautified by using the :meth:`~sqlparse.format` function.

.. code-block:: python

  >>> sql = 'select * from foo where id in (select id from bar);'
  >>> print(sqlparse.format(sql, reindent=True, keyword_case='upper'))
  SELECT *
  FROM foo
  WHERE id IN
      (SELECT id
       FROM bar);

In this case all keywords in the given SQL are uppercased and the
indentation is changed to make it more readable. Read :ref:`formatting` for
a full reference of supported options given as keyword arguments
to that function.

Before proceeding with a closer look at the internal representation of
SQL statements, you should be aware that this SQL parser is intentionally
non-validating. It assumes that the given input is at least some kind
of SQL and then it tries to analyze as much as possible without making
too much assumptions about the concrete dialect or the actual statement.
At least it's up to the user of this API to interpret the results right.

When using the :meth:`~sqlparse.parse` function a tuple of
:class:`~sqlparse.sql.Statement` instances is returned:

.. code-block:: python

  >>> sql = 'select * from "someschema"."mytable" where id = 1'
  >>> parsed = sqlparse.parse(sql)
  >>> parsed
  (<Statement 'select...' at 0x9ad08ec>,)

Each item of the tuple is a single statement as identified by the above
mentioned :meth:`~sqlparse.split` function. So let's grab the only element
from that list and have a look at the ``tokens`` attribute.
Sub-tokens are stored in this attribute.

.. code-block:: python

  >>> stmt = parsed[0]  # grab the Statement object
  >>> stmt.tokens
  [<DML 'select' at 0x7f6b8c1b5f40>,
   <Whitespace ' ' at 0x7f6b8c1b5fa0>,
   <Wildcard '*' at 0x7f6b8c1b6000>,
   <Whitespace ' ' at 0x7f6b8c1b6060>,
   <Keyword 'from' at 0x7f6b8c1b60c0>,
   <Whitespace ' ' at 0x7f6b8c1b6120>,
   <Identifier '"somes...' at 0x7f6b8c1a89d0>,
   <Whitespace ' ' at 0x7f6b8c1b6180>,
   <Where 'where ...' at 0x7f6b8c1a8a40>]

Each object can be converted back to a string at any time:

.. code-block:: python

   >>> str(stmt)
   'select * from "someschema"."mytable" where id = 1'
   >>> str(stmt.tokens[-1])  # or just the WHERE part
   'where id = 1'

Details of the returned objects are described in :ref:`analyze`.


Development & Contributing
--------------------------

To check out the latest sources of this module run

.. code-block:: bash

   $ git clone https://github.com/andialbrecht/sqlparse.git

:mod:`sqlparse` is tested under Python 3.10+ and PyPy. Tests are run
automatically for each commit and pull request on `GitHub Actions
<https://github.com/andialbrecht/sqlparse/actions>`_.

The project uses `uv <https://docs.astral.sh/uv/>`_ to manage dependencies
and environments. Make sure to run the test suite before sending a pull
request:

.. code-block:: bash

   $ make test

To check the code for style issues run

.. code-block:: bash

   $ make lint

Please file bug reports and feature requests on the project site at
https://github.com/andialbrecht/sqlparse/issues/new.
