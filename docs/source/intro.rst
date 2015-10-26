Introduction
============


Download & Installation
-----------------------

The latest released version can be obtained from the `Python Package
Index (PyPI) <http://pypi.python.org/pypi/sqlparse/>`_. To extract the
install the module system-wide run

.. code-block:: bash

   $ tar cvfz python-sqlparse-VERSION.tar.gz
   $ cd python-sqlparse/
   $ sudo python setup.py install

Alternatively you can install :mod:`sqlparse` using :command:`pip`:

.. code-block:: bash

   $ pip install sqlparse


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
  [u'select * from foo; ', u'select * from bar;']

The end of a statement is identified by the occurrence of a semicolon.
Semicolons within certain SQL constructs like ``BEGIN ... END`` blocks
are handled correctly by the splitting mechanism.

SQL statements can be beautified by using the :meth:`~sqlarse.format` function.

.. code-block:: python

  >>> sql = 'select * from foo where id in (select id from bar);'
  >>> print sqlparse.format(sql, reindent=True, keyword_case='upper')
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
  (<DML 'select' at 0x9b63c34>,
   <Whitespace ' ' at 0x9b63e8c>,
   <Operator '*' at 0x9b63e64>,
   <Whitespace ' ' at 0x9b63c5c>,
   <Keyword 'from' at 0x9b63c84>,
   <Whitespace ' ' at 0x9b63cd4>,
   <Identifier '"somes...' at 0x9b5c62c>,
   <Whitespace ' ' at 0x9b63f04>,
   <Where 'where ...' at 0x9b5caac>)

Each object can be converted back to a string at any time:

.. code-block:: python

   >>> str(stmt)  # str(stmt) for Python 3
   'select * from "someschema"."mytable" where id = 1'
   >>> str(stmt.tokens[-1])  # or just the WHERE part
   'where id = 1'

Details of the returned objects are described in :ref:`analyze`.


Development & Contributing
--------------------------

To check out the latest sources of this module run

.. code-block:: bash

   $ git clone git://github.com/andialbrecht/sqlparse.git


to check out the latest sources from the repository.

:mod:`sqlparse` is currently tested under Python 2.5, 2.6, 2.7, 3.2 and
pypy. Tests are automatically run on each commit and for each pull
request on Travis: https://travis-ci.org/andialbrecht/sqlparse

Make sure to run the test suite before sending a pull request by running

.. code-block:: bash

   $ tox

It's ok, if :command:`tox` doesn't find all interpreters listed
above. Ideally a Python 2 and a Python 3 version should be tested
locally.

Please file bug reports and feature requests on the project site at
https://github.com/andialbrecht/sqlparse/issues/new or if you have
code to contribute upload it to http://codereview.appspot.com and
add albrecht.andi@googlemail.com as reviewer.

For more information about the review tool and how to use it visit
it's project page: http://code.google.com/p/rietveld.
