"""Parse throughput benchmark for realistic large SQL.

The other benchmarks here measure pathological shapes tied to specific
advisories; this one measures the ordinary case, the large varied SQL that
BI tools and ETL jobs generate.  A plain slowdown shows up in the ``kB/s``
column rather than in the exponent -- a uniform 2x regression leaves the
exponent at 1.0.

Run with:  python benchmarks/bench_parse_throughput.py
           python benchmarks/bench_parse_throughput.py --profile
"""

import sys

from _harness import Vector, main

import sqlparse
from sqlparse.engine import grouping

# Disable the grouping-stage DoS guards.  They are a policy limit on
# untrusted input, not a property of the engine: realistic SQL of the size
# measured here exceeds MAX_GROUPING_TOKENS and would be rejected outright.
grouping.MAX_GROUPING_DEPTH = None
grouping.MAX_GROUPING_TOKENS = None


def analytics_query(n):
    """One CTE selecting n expressions, each with a CASE and a window
    function, over a 7-way join, with a long IN list and a GROUP BY."""
    projections = ',\n'.join(
        f"""        t{i % 7}.col_{i} AS alias_{i},
        CASE WHEN t{i % 7}.flag_{i} = 'Y' AND t{i % 7}.amt_{i} > {i}.5
             THEN COALESCE(t{i % 7}.amt_{i} * 1.075, 0)
             ELSE NULL END AS calc_{i},
        SUM(t{i % 7}.amt_{i}) OVER (
            PARTITION BY t{i % 7}.grp_{i} ORDER BY t{i % 7}.dt_{i}
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS win_{i}"""
        for i in range(n))
    joins = ''.join(
        f"    LEFT JOIN schema_a.table_{i} t{i} "
        f"ON t{i}.id = t0.id AND t{i}.dt >= DATE '2024-01-01'\n"
        for i in range(1, 7))
    in_list = ', '.join(f"'st_{i}'" for i in range(n))
    group_by = ', '.join(f't0.grp_{i}' for i in range(max(n // 4, 1)))
    return (
        f'WITH base AS (\n    SELECT\n{projections}\n'
        f'    FROM schema_a.table_0 t0\n{joins}'
        f'    WHERE t0.status IN ({in_list})\n'
        f"      AND t0.region = 'EMEA'  -- restrict region\n"
        f'    GROUP BY {group_by}\n'
        f'    HAVING COUNT(*) > 10\n)\n'
        f'SELECT * FROM base ORDER BY alias_0 DESC')


def statement_script(n):
    """A migration-style script of n separate statements."""
    return '\n'.join(
        f"UPDATE tbl_{i % 20} SET col_a = 'v{i}', col_b = {i} "
        f"WHERE id = {i} AND flag = 'Y';"
        for i in range(n))


def union_all_chain(n):
    """n branches unioned together, the shape generated pivots produce."""
    return '\nUNION ALL\n'.join(
        f"SELECT {i} AS bucket, col_a, col_b FROM src_{i % 12} "
        f"WHERE dt = DATE '2024-01-{i % 28 + 1:02d}' AND col_c > {i}"
        for i in range(n))


def string_and_comment_heavy(n):
    """Comment lines, escaped string literals and inline comments."""
    return '\n'.join(
        f'-- comment line {i} explaining the next bit\n'
        f"SELECT 'literal {i} with ''escaped'' quotes', /* inline {i} */ "
        f"col_{i} FROM t WHERE x = '{i}';"
        for i in range(n))


def reindent(sql):
    return sqlparse.format(sql, reindent=True)


VECTORS = [
    Vector('analytics query (CTE, joins, windows)',
           analytics_query, (25, 50, 100, 200)),
    Vector('multi-statement script',
           statement_script, (100, 200, 400, 800)),
    Vector('UNION ALL chain',
           union_all_chain, (100, 200, 400, 800)),
    Vector('string and comment heavy',
           string_and_comment_heavy, (150, 300, 600, 1200)),
    Vector('analytics query, format(reindent=True)',
           analytics_query, (25, 50, 100, 200), reindent),
]

if __name__ == '__main__':
    sys.exit(main('parse throughput', VECTORS,
                  note='realistic large SQL -- watch the kB/s column',
                  argv=sys.argv[1:]))
