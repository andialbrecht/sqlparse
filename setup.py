# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This setup script is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

import os
from distutils.core import setup

import sqlparse


def find_packages(base):
    ret = [base]
    for path in os.listdir(base):
        if path.startswith('.'):
            continue
        full_path = os.path.join(base, path)
        if os.path.isdir(full_path):
            ret += find_packages(full_path)
    return ret


LONG_DESCRIPTION = """
``sqlparse`` is a non-validating SQL parser module.
It provides support for parsing, splitting and formatting SQL statements.

Visit the `project page <http://code.google.com/p/python-sqlparse/>`_ for
additional information and documentation.

**Example Usage**


Splitting SQL statements::

   >>> import sqlparse
   >>> sqlparse.split('select * from foo; select * from bar;')
   [u'select * from foo; ', u'select * from bar;']


Formatting statemtents::

   >>> sql = 'select * from foo where id in (select id from bar);'
   >>> print sqlparse.format(sql, reindent=True, keyword_case='upper')
   SELECT *
   FROM foo
   WHERE id IN
     (SELECT id
      FROM bar);


Parsing::

   >>> sql = 'select * from someschema.mytable where id = 1'
   >>> res = sqlparse.parse(sql)
   >>> res
   (<Statement 'select...' at 0x9ad08ec>,)
   >>> stmt = res[0]
   >>> stmt.to_unicode()  # converting it back to unicode
   u'select * from someschema.mytable where id = 1'
   >>> # This is how the internal representation looks like:
   >>> stmt.tokens
   (<DML 'select' at 0x9b63c34>,
    <Whitespace ' ' at 0x9b63e8c>,
    <Operator '*' at 0x9b63e64>,
    <Whitespace ' ' at 0x9b63c5c>,
    <Keyword 'from' at 0x9b63c84>,
    <Whitespace ' ' at 0x9b63cd4>,
    <Identifier 'somes...' at 0x9b5c62c>,
    <Whitespace ' ' at 0x9b63f04>,
    <Where 'where ...' at 0x9b5caac>)

"""


DOWNLOAD_URL = ('http://python-sqlparse.googlecode.com/files/'
                'sqlparse-%s.tar.gz' % sqlparse.__version__)


setup(
    name='sqlparse',
    version=sqlparse.__version__,
    packages=find_packages('sqlparse'),
    description='Non-validating SQL parser',
    author='Andi Albrecht',
    author_email='albrecht.andi@gmail.com',
    download_url=DOWNLOAD_URL,
    long_description=LONG_DESCRIPTION,
    license='BSD',
    url='http://python-sqlparse.googlecode.com/',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Topic :: Database',
        'Topic :: Software Development'
    ],
    scripts=['bin/sqlformat'],
)
