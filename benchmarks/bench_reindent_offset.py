"""Reindentation offset benchmark (GHSA-cfqr-cjx5-5jcm, CWE-1333).

Measures ``format(sql, reindent=True)`` for SQL that stresses
``ReindentFilter._get_offset()``, which reports the column a token starts
on.  It used to rebuild the statement prefix from the start of the
statement on every call, and it is called once per group -- so
reindenting a list of n parenthesized tuples cost O(n^2).  An attacker
who controls SQL sent to this opt-in path can size a tuple list to stay
just below the grouping-token cap (``MAX_GROUPING_TOKENS``), so grouping
succeeds and the expensive reindentation path is entered.

Both shapes reach the same offset calculation through different filters:
``IN (...)`` tuple lists via ``_process_parenthesis()`` and
``_process_identifierlist()``, ``VALUES`` lists via ``_process_values()``.
Sizes stay below the grouping-token cap; larger input is rejected by the
cap instead of reaching the measured path.

Run with:  python benchmarks/bench_reindent_offset.py
"""

import sys

from _harness import Vector, main

import sqlparse


def in_tuple_list(n):
    """WHERE ... IN with n tuples -- the shape from the advisory."""
    tuples = ', '.join(f'({i}, {i * 2})' for i in range(n))
    return f'SELECT a FROM t WHERE (col1, col2) IN ({tuples})'


def values_list(n):
    """INSERT ... VALUES with n tuples -- reaches _process_values()."""
    tuples = ', '.join(f'({i})' for i in range(n))
    return f'INSERT INTO t VALUES {tuples}'


def reindent(sql):
    return sqlparse.format(sql, reindent=True)


VECTORS = [
    Vector('IN-tuple list', in_tuple_list, (150, 300, 600, 1200), reindent),
    Vector('VALUES list', values_list, (250, 500, 1000, 1950), reindent),
]

if __name__ == '__main__':
    sys.exit(main('reindentation offsets', VECTORS,
                  note='GHSA-cfqr-cjx5-5jcm -- sqlparse.format(reindent=True)',
                  argv=sys.argv[1:]))
