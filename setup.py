#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Andi Albrecht, albrecht.andi@gmail.com
#
# This setup script is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php

import re

from setuptools import setup, find_packages


def get_version():
    """Parse __init__.py for version number instead of importing the file."""
    VERSIONFILE = 'sqlparse/__init__.py'
    VSRE = r'^__version__ = [\'"]([^\'"]*)[\'"]'
    with open(VERSIONFILE) as f:
        verstrline = f.read()
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        return mo.group(1)
    raise RuntimeError('Unable to find version in {fn}'.format(fn=VERSIONFILE))


LONG_DESCRIPTION = """
``sqlparse`` is a non-validating SQL parser module.
It provides support for parsing, splitting and formatting SQL statements.

Visit the `project page <https://github.com/andialbrecht/sqlparse>`_ for
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
   >>> str(stmt)  # converting it back to unicode
   'select * from someschema.mytable where id = 1'
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

setup(
    name='sqlparse',
    version=get_version(),
    author='Andi Albrecht',
    author_email='albrecht.andi@gmail.com',
    url='https://github.com/andialbrecht/sqlparse',
    description='Non-validating SQL parser',
    long_description=LONG_DESCRIPTION,
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Database',
        'Topic :: Software Development',
    ],
    packages=find_packages(exclude=('tests',)),
    entry_points={
        'console_scripts': [
            'sqlformat = sqlparse.__main__:main',
        ]
    },
)
