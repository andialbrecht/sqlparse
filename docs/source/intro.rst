Introduction
============

:mod:`sqlparse` is a non-validating SQL parser for Python.
It provides support for parsing, splitting and formatting SQL statements.
The module is released under the terms of the
`New BSD license <http://www.opensource.org/licenses/bsd-license.php>`_.

Visit the project page at http://python-sqlparse.googlecode.com for
further information about this project.


Download & Installation
-----------------------

The latest released version can be obtained from the
`downloads page <http://code.google.com/p/python-sqlparse/downloads/list>`_
on the project's website. To extract the source archive and to install
the module on your system run

.. code-block:: bash

   $ tar cvfz python-sqlparse-VERSION.tar.gz
   $ cd python-sqlparse/
   $ sudo python setup.py install

Alternatively you can install :mod:`sqlparse` from the
`Python Packge Index <http://pypi.python.org/pypi/sqlparse>`_ with your
favorite tool for installing Python modules. For example when using
`pip <http://pypi.python.org/pypi/pip>`_ run :command:`pip install sqlparse`.


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

   >>> stmt.to_unicode()
   u'select * from "someschema"."mytable" where id = 1'
   >>> stmt.tokens[-1].to_unicode()  # or just the WHERE part
   u'where id = 1'

Details of the returned objects are described in :ref:`analyze`.


Development & Contributing
--------------------------

To check out the latest sources of this module run

.. code-block:: bash

   $ hg clone http://python-sqlparse.googlecode.com/hg/ python-sqlparse


to check out the latest sources from the Mercurial repository.

Please file bug reports and feature requests on the project site at
http://code.google.com/p/python-sqlparse/issues/entry or if you have
code to contribute upload it to http://codereview.appspot.com and
add albrecht.andi@googlemail.com as reviewer.

For more information about the review tool and how to use it visit
it's project page: http://code.google.com/p/rietveld.
