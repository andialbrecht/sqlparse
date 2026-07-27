.. python-sqlparse documentation master file, created by
   sphinx-quickstart on Thu Feb 26 08:19:28 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

python-sqlparse
===============

.. NOTE: This section duplicates the introduction from ../../README.md.
   It used to be included from README.rst directly. The README is Markdown
   now, so the text is kept in sync manually until the docs are migrated to
   Markdown as well.

A non-validating SQL parser for Python. Split scripts into statements, format
them, and walk their token tree.

sqlparse tokenizes SQL text and groups the parts it recognizes into a tree of
statements, clauses, identifiers and expressions. It accepts any input without
validating it, and makes no assumptions about a particular SQL dialect, so
vendor extensions and templated SQL parse too. It is a building block for
formatters, linters, editors and query analysis tools.

Requires Python 3.10+. Licensed under the
`New BSD license <https://opensource.org/licenses/BSD-3-Clause>`_.

Contents
--------

.. toctree::
   :maxdepth: 2

   intro
   api
   analyzing
   ui
   extending
   changes
   license
   indices


Resources
---------

Project page
   https://github.com/andialbrecht/sqlparse

Bug tracker
   https://github.com/andialbrecht/sqlparse/issues

Documentation
   https://sqlparse.readthedocs.io/

Online Demo
  https://sqlformat.org/

