# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This setup script is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

import re
import sys

try:
    from setuptools import setup, find_packages
    packages = find_packages(exclude=('tests',))
except ImportError:
    if sys.version_info[0] == 3:
        raise RuntimeError('distribute is required to install this package.')
    from distutils.core import setup
    packages = ['sqlparse', 'sqlparse.engine']


def get_version():
    """parse __init__.py for version number instead of importing the file

    see http://stackoverflow.com/questions/458550/standard-way-to-embed-version-into-python-package
    """
    VERSIONFILE='sqlparse/__init__.py'
    verstrline = open(VERSIONFILE, "rt").read()
    VSRE = r'^__version__ = [\'"]([^\'"]*)[\'"]'
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError('Unable to find version string in %s.'
                           % (VERSIONFILE,))


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
   >>> unicode(stmt)  # converting it back to unicode
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

VERSION = get_version()


kwargs = {}
if sys.version_info[0] == 3:
    kwargs['use_2to3'] = True


setup(
    name='sqlparse',
    version=VERSION,
    packages=packages,
    description='Non-validating SQL parser',
    author='Andi Albrecht',
    author_email='albrecht.andi@gmail.com',
    long_description=LONG_DESCRIPTION,
    license='BSD',
    url='https://github.com/andialbrecht/sqlparse',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Database',
        'Topic :: Software Development'
    ],
    scripts=['bin/sqlformat'],
    **kwargs
)
