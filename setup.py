# Copyright (C) 2008 Andi Albrecht, albrecht.andi@gmail.com
#
# This setup script is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

from distutils.core import setup

setup(
    name='sqlparse',
    version='0.1.0',
    py_modules=['sqlparse'],
    description='Non-validating SQL parser',
    author='Andi Albrecht',
    author_email='albrecht.andi@gmail.com',
    #long_description=release.long_description,
    license='BSD',
    url='http://python-sqlparse.googlecode.com/',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Software Development'
    ],
    scripts=['bin/sqlformat'],
)
