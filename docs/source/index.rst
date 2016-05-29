.. python-sqlparse documentation master file, created by
   sphinx-quickstart on Thu Feb 26 08:19:28 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

python-sqlparse
===============

:mod:`sqlparse` is a non-validating SQL parser for Python.
It provides support for parsing, splitting and formatting SQL statements.

The module is compatible with Python 2.7 and Python 3 (>= 3.3)
and released under the terms of the `New BSD license
<http://www.opensource.org/licenses/bsd-license.php>`_.

Visit the project page at https://github.com/andialbrecht/sqlparse for
further information about this project.


tl;dr
-----

.. code-block:: bash

   $ pip install sqlparse
   $ python
   >>> import sqlparse
   >>> print(sqlparse.format('select * from foo', reindent=True))
   select *
   from foo
   >>> parsed = sqlparse.parse('select * from foo')[0]
   >>> parsed.tokens
   [<DML 'select' at 0x7f22c5e15368>, <Whitespace ' ' at 0x7f22c5e153b0>, <Wildcard '*' … ]
   >>>


Contents
--------

.. toctree::
   :maxdepth: 2

   intro
   api
   analyzing
   ui
   changes
   indices


Resources
---------

Project page
   https://github.com/andialbrecht/sqlparse

Bug tracker
   https://github.com/andialbrecht/sqlparse/issues

Documentation
   https://sqlparse.readthedocs.io/
