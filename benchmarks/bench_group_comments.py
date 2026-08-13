"""Comment grouping benchmark (GHSA-f2ff-p2ww-7p4p).

Measures a statement made only of single-line comments (``'-- c\\n'``
repeated n times).  Such input lexes in O(n), but ``group_comments()``
used to rescan the O(n) remaining tokens for every comment token, giving
O(n^2) total work.  ``group_comments()`` runs first in ``group()``,
before the ``MAX_GROUPING_TOKENS`` guard, so the token cap does not
protect this vector.

Both entry points that reach the path are measured: ``parse()`` and
``format(sql, strip_comments=True)``.

Run with:  python benchmarks/bench_group_comments.py
"""

import sys

from _harness import Vector, main

import sqlparse


def comment_only_statement(n):
    return '-- c\n' * n


SIZES = (1000, 2000, 4000, 8000)

VECTORS = [
    Vector('parse', comment_only_statement, SIZES),
    Vector('format strip_comments=True', comment_only_statement, SIZES,
           lambda sql: sqlparse.format(sql, strip_comments=True)),
]

if __name__ == '__main__':
    sys.exit(main('comment grouping', VECTORS,
                  note='GHSA-f2ff-p2ww-7p4p', argv=sys.argv[1:]))
