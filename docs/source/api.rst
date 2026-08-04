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

``reindent_aligned``
  If ``True`` the indentations of the statements are changed, and statements are aligned by keywords.

``use_space_around_operators``
  If ``True`` spaces are used around all operators.

``indent_tabs``
  If ``True`` tabs instead of spaces are used for indentation.

``indent_width``
  The width of the indentation, defaults to 2.

``indent_after_first``
  If ``True`` the indentation is added after the first line of a statement,
  for example after ``SELECT``.

``indent_columns``
  If ``True`` all columns are indented by ``indent_width`` instead of the
  length of the preceding keyword.

``strip_whitespace``
  If ``True`` repeated whitespace is collapsed into single spaces. This is
  implied by ``reindent`` and ``reindent_aligned``.

``wrap_after``
  The column limit (in characters) for wrapping comma-separated lists. If unspecified, it
  puts every item in the list on its own line.

``compact``
  If ``True`` the formatter tries to produce more compact output.

``output_format``
  If given the output is additionally formatted to be used as a variable
  in a programming language. Allowed values are "python" and "php".

``comma_first``
  If ``True`` comma-first notation for column names is used.


Security and Performance Considerations
---------------------------------------

For developers working with very large SQL statements or in security-sensitive
environments, sqlparse includes built-in protections against potential denial
of service (DoS) attacks:

**Grouping Limits**
  The parser includes configurable limits to prevent excessive resource
  consumption when processing very large or deeply nested SQL structures:

  - ``MAX_GROUPING_DEPTH`` (default: 100) - Limits recursion depth during token grouping
  - ``MAX_GROUPING_TOKENS`` (default: 10,000) - Limits the number of tokens processed in a single grouping operation

  These limits can be modified by changing the constants in ``sqlparse.engine.grouping``
  if your application requires processing larger SQL statements. Set a limit to ``None``
  to completely disable it. However, increasing these values or disabling limits may
  expose your application to DoS vulnerabilities when processing untrusted SQL input.

  Example of modifying limits::

    import sqlparse.engine.grouping

    # Increase limits (use with caution)
    sqlparse.engine.grouping.MAX_GROUPING_DEPTH = 200
    sqlparse.engine.grouping.MAX_GROUPING_TOKENS = 50000

    # Disable limits completely (use with extreme caution)
    sqlparse.engine.grouping.MAX_GROUPING_DEPTH = None
    sqlparse.engine.grouping.MAX_GROUPING_TOKENS = None

.. warning::
   Increasing the grouping limits or disabling them completely may make your
   application vulnerable to DoS attacks when processing untrusted SQL input.
   Only modify these values if you are certain about the source and size of
   your SQL statements.
