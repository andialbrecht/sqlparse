:mod:`sqlparse` -- Parse SQL statements
=======================================

.. module:: sqlparse
   :synopsis: Parse SQL statements.

The :mod:`sqlparse` module provides the following functions on module-level.

.. autofunction:: sqlparse.split

.. autofunction:: sqlparse.format

.. autofunction:: sqlparse.parse

In most cases there's no need to set the `encoding` parameter. If
`encoding` is not set, sqlparse assumes that the given SQL statement
is encoded either in utf-8 or latin-1.


.. _formatting:

Formatting of SQL Statements
----------------------------

The :meth:`~sqlparse.format` function accepts the following keyword arguments.

``keyword_case``
  Changes how keywords are formatted. Allowed values are "upper", "lower"
  and "capitalize".

``identifier_case``
  Changes how identifiers are formatted. Allowed values are "upper", "lower",
  and "capitalize".

``strip_comments``
  If ``True`` comments are removed from the statements.

``truncate_strings``
  If ``truncate_strings`` is a positive integer, string literals longer than
  the given value will be truncated.

``truncate_char`` (default: "[...]")
  If long string literals are truncated (see above) this value will be append
  to the truncated string.

``reindent``
  If ``True`` the indentations of the statements are changed.

``indent_tabs``
  If ``True`` tabs instead of spaces are used for indentation.

``indent_width``
  The width of the indentation, defaults to 2.

``wrap_after``
  The column limit for wrapping comma-separated lists. If unspecified, it
  puts every item in the list on its own line.

``output_format``
  If given the output is additionally formatted to be used as a variable
  in a programming language. Allowed values are "python" and "php".
