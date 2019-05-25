python-sqlparse - Parse SQL statements
======================================

sqlparse is a non-validating SQL parser module for Python.

|buildstatus|_
|coverage|_


Install
-------

Using pip::

    $ pip install sqlparse

From the repository, run::

  python setup.py install

to install sqlparse on your system.

sqlparse is compatible with Python 2.7 and Python 3 (>= 3.4).


Quick Start
-----------

code-block:: python

   >>> import sqlparse
   >>> # Split a string containing two SQL statements:
   >>> statements = sqlparse.split('select * from foo; select * from bar;')
   >>> # Format the first statement and print it out:
   >>> print(sqlparse.format(statements[0], reindent=True, keyword_case='upper'))
   SELECT *
   FROM foo;
   >>>

Links
-----

Project Page
  https://github.com/andialbrecht/sqlparse

Documentation
  https://sqlparse.readthedocs.io/en/latest/

Issues/Bugs
  https://github.com/andialbrecht/sqlparse/issues

Online Demo
  https://sqlformat.org/


sqlparse is licensed under the BSD license.

Parts of the code are based on pygments written by Georg Brandl and others.
pygments-Homepage: http://pygments.org/

.. |buildstatus| image:: https://secure.travis-ci.org/andialbrecht/sqlparse.png?branch=master
.. _buildstatus: https://travis-ci.org/#!/andialbrecht/sqlparse
.. |coverage| image:: https://coveralls.io/repos/andialbrecht/sqlparse/badge.svg?branch=master&service=github
.. _coverage: https://coveralls.io/github/andialbrecht/sqlparse?branch=master
