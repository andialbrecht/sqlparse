Introduction
============

:mod:`sqlparse` is a non-validating SQL parser for Python.

It provides support for parsing, splitting and formatting SQL statements.

:mod:`sqlparse` is released under the terms of the
`New BSD license <http://www.opensource.org/licenses/bsd-license.php>`_.

Visit http://sqlformat.appspot.com to try it's formatting features.


Download & Installation
-----------------------

To download and install :mod:`sqlparse` on your system run the following
commands:

.. code-block:: bash

  $ git clone git://github.com/andialbrecht/python-sqlparse.git
  $ cd python-sqlparse.git/
  $ sudo python setup.py install

A tarball of the current sources is available under the following URL:
http://github.com/andialbrecht/python-sqlparse/tarball/master


Example Usage
-------------

Here are some usage examples of this module.

Splitting statements::

  >>> import sqlparse
  >>> sql = 'select * from foo; select * from bar;'
  >>> sqlparse.split(sql)
  <<< [u'select * from foo; ', u'select * from bar;']

Formatting statemtents::

  >>> sql = 'select * from foo where id in (select id from bar);'
  >>> print sqlparse.format(sql, reindent=True, keyword_case='upper')
  SELECT *
  FROM foo
  WHERE id IN
    (SELECT id
     FROM bar);

Now, let's have a deeper look at the internals::

  >>> sql = 'select * from "someschema"."mytable" where id = 1'
  >>> pared = sqlparse.parse(sql)
  >>> pared
  <<< (<Statement 'select...' at 0x9ad08ec>,)
  >>> stmt = parsed[0]
  >>> stmt.to_unicode()  # converting it back to unicode
  <<< u'select * from "someschema"."mytable" where id = 1'
  >>> # This is how the internal representation looks like:
  >>> stmt.tokens
  <<<
  (<DML 'select' at 0x9b63c34>,
   <Whitespace ' ' at 0x9b63e8c>,
   <Operator '*' at 0x9b63e64>,
   <Whitespace ' ' at 0x9b63c5c>,
   <Keyword 'from' at 0x9b63c84>,
   <Whitespace ' ' at 0x9b63cd4>,
   <Identifier '"somes...' at 0x9b5c62c>,
   <Whitespace ' ' at 0x9b63f04>,
   <Where 'where ...' at 0x9b5caac>)
  >>>


.. todo:: Describe general concepts
   Why non-validating? Processing stages (tokens, groups,...), filter,


Development & Contributing
--------------------------

Please file bug reports and feature requests on the project site at
http://code.google.com/p/python-sqlparse/issues/entry or if you have
code to contribute upload it to http://codereview.appspot.com and
add albrecht.andi@googlemail.com as reviewer.

For more information about the review tool and how to use it visit
it's project page: http://code.google.com/p/rietveld.
