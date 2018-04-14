python-sqlparse - Parse SQL statements
======================================

sqlparse is a non-validating SQL parser module for Python.

|buildstatus|_
|coverage|_


Install
-------

From pip, run::

    $ pip install --upgrade sqlparse

Consider using the ``--user`` option_.

.. _option: https://pip.pypa.io/en/latest/user_guide/#user-installs

From the repository, run::

  python setup.py install

to install python-sqlparse on your system.

python-sqlparse is compatible with Python 2.7 and Python 3 (>= 3.3).


Run Tests
---------

To run the test suite run::

  tox

Note, you'll need tox installed, of course.


Links
-----

Project Page
  https://github.com/andialbrecht/sqlparse

Documentation
  https://sqlparse.readthedocs.io/en/latest/

Discussions
  https://groups.google.com/forum/#!forum/sqlparse

Issues/Bugs
  https://github.com/andialbrecht/sqlparse/issues

Online Demo
  https://sqlformat.org/


python-sqlparse is licensed under the BSD license.

Parts of the code are based on pygments written by Georg Brandl and others.
pygments-Homepage: http://pygments.org/

.. |buildstatus| image:: https://secure.travis-ci.org/andialbrecht/sqlparse.png?branch=master
.. _buildstatus: https://travis-ci.org/#!/andialbrecht/sqlparse
.. |coverage| image:: https://coveralls.io/repos/andialbrecht/sqlparse/badge.svg?branch=master&service=github
.. _coverage: https://coveralls.io/github/andialbrecht/sqlparse?branch=master
