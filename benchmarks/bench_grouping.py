"""Grouping performance benchmarks.

Measures parse time for SQL patterns that stress the grouping engine:
- Deeply nested parentheses
- Deeply nested CASE WHEN expressions
- Wide column lists (tests O(N) identifier grouping, fixed in PR848)

Run with:  python benchmarks/bench_grouping.py
"""

import signal
import time

import sqlparse


def _alarm_handler(signum, frame):
    raise TimeoutError()


signal.signal(signal.SIGALRM, _alarm_handler)


def measure(label, sql, fn):
    signal.alarm(30)
    t0 = time.perf_counter()
    status = 'OK'
    try:
        fn(sql)
    except sqlparse.exceptions.SQLParseError:
        status = 'CAP'
    except TimeoutError:
        status = 'TIMEOUT'
    finally:
        signal.alarm(0)
    dt = (time.perf_counter() - t0) * 1000
    print(f'  {status:8} {dt:8.1f} ms  {label}  ({len(sql)} B)')


# Vector 1: deeply nested parentheses
print('Nested parentheses:')
for n in (200, 500, 1000, 2000):
    sql = 'SELECT ' + '(' * n + '1' + ')' * n
    measure(f'nested-paren n={n}', sql, sqlparse.parse)

# Vector 2: deeply nested CASE WHEN
print('Nested CASE WHEN:')
for n in (100, 200, 400):
    case = '1'
    for i in range(n):
        case = f'CASE WHEN x={i} THEN {case} ELSE NULL END'
    measure(f'CASE-nested n={n}', f'SELECT {case} FROM t', sqlparse.parse)

# Vector 3: wide column lists (O(N) grouping, regression fixed in PR848)
print('Wide column lists:')
for n in (500, 1000, 2000, 4000):
    cols = ', '.join(f'col_{i}' for i in range(n))
    sql = f'SELECT {cols} FROM t'
    measure(f'wide-select n={n}', sql, sqlparse.parse)
