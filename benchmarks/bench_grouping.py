"""Grouping engine benchmark.

Measures parse time for SQL patterns that stress the grouping engine:

- Deeply nested parentheses and CASE WHEN expressions, which drive the
  recursion in ``_group_matching()`` and the ``TokenList`` constructor.
- Wide column lists, which used to rebuild the group value on every
  extend step and therefore cost O(n^2) in the number of columns (pr848).

Run with:  python benchmarks/bench_grouping.py
"""

import sys

from _harness import Vector, main

from sqlparse.engine import grouping

# Disable the grouping-stage DoS guards.  They are a policy limit on
# untrusted input, not a property of the engine: with them in place every
# size below would be rejected before the measured work happens.
grouping.MAX_GROUPING_DEPTH = None
grouping.MAX_GROUPING_TOKENS = None
sys.setrecursionlimit(20000)


def nested_parentheses(n):
    return 'SELECT ' + '(' * n + '1' + ')' * n


def nested_case_when(n):
    case = '1'
    for i in range(n):
        case = f'CASE WHEN x={i} THEN {case} ELSE NULL END'
    return f'SELECT {case} FROM t'


def wide_column_list(n):
    columns = ', '.join(f'col_{i}' for i in range(n))
    return f'SELECT {columns} FROM t'


VECTORS = [
    Vector('nested parentheses', nested_parentheses, (200, 500, 1000, 2000)),
    Vector('nested CASE WHEN', nested_case_when, (100, 200, 400)),
    Vector('wide column lists', wide_column_list, (500, 1000, 2000, 4000)),
]

if __name__ == '__main__':
    sys.exit(main('grouping engine', VECTORS,
                  note='sqlparse.parse', argv=sys.argv[1:]))
