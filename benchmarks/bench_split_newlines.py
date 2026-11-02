"""Newline splitting benchmark (GHSA-3r5h-5jcg-gmgg, CWE-1333).

Measures ``format(sql)`` with default options for SQL that stresses
``split_unquoted_newlines()``, which the serializer runs on every
formatted statement.  It used a regular expression that, for every quote
that is never closed, scanned to the end of the text before giving up --
so n unclosed quotes cost O(n^2).  The grouping caps don't help here:
the payload has few tokens because the lexer keeps the escaped quotes
together.

Run with:  python benchmarks/bench_split_newlines.py
"""

import sys

from _harness import Vector, main

import sqlparse


def unclosed_double_quotes(n):
    """n times a double quote followed by a backslash."""
    return '"\\' * n


def unclosed_single_quotes(n):
    """Same with single quotes, after a SELECT keyword."""
    return 'SELECT ' + "\\'" * n


VECTORS = [
    Vector('unclosed double quotes', unclosed_double_quotes,
           (5000, 10000, 20000, 40000), sqlparse.format),
    Vector('unclosed single quotes', unclosed_single_quotes,
           (5000, 10000, 20000, 40000), sqlparse.format),
]

if __name__ == '__main__':
    sys.exit(main('newline splitting', VECTORS,
                  note='GHSA-3r5h-5jcg-gmgg -- sqlparse.format()',
                  argv=sys.argv[1:]))
