"""Delimited-literal lexer benchmark (GHSA-prg7-hcfm-mfcr).

Measures parse time for SQL text containing many unique, unmatched
opening delimiters for the two lexer constructs that used a lazy dot-all
regex (`[\\s\\S]*?`) terminated by a backreference or a literal closing
sequence:

- Dollar-quoted literals, e.g. `$a0$x $a1$x ... $aN$x` (backreference).
- Multiline comments, e.g. `/* unique0 ... /* unique1 ...` (literal `*/`).

When no closing delimiter is present, a lazy dot-all quantifier applied at
every text position must scan to the end of the remaining input for every
opener, which is O(n^2) total work as the number of openers grows.

This benchmark does not assert a pass/fail threshold, since absolute timings
and scaling ratios depend on the host machine. It exists to make the
runtime characteristics of these code paths observable and to let it be
re-run (e.g. after a fix) to confirm that scaling has improved.

Run with:  python benchmarks/bench_dollar_quote_redos.py
"""

import signal
import time

import sqlparse
from sqlparse.engine import grouping

# Disable the grouping-stage DoS guards. They fire only after lexing
# completes and do not bound regex CPU time, so they would otherwise mask
# the lexer's true (unbounded) timing behind a SQLParseError at larger n.
grouping.MAX_GROUPING_DEPTH = None
grouping.MAX_GROUPING_TOKENS = None


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
    return dt


def make_dollar_quote_payload(n):
    # N unique, never-closed dollar-quote openers. Each is unique so the
    # backreference regex cannot short-circuit on an earlier match.
    return ' '.join(f'$a{i}$x' for i in range(n))


def make_comment_payload(n):
    # N unique, never-closed multiline comment openers. No '*/' appears
    # anywhere, so the closing literal can never short-circuit the scan.
    return ' '.join(f'/* unique{i} comment never closed' for i in range(n))


def run_scaling(label, make_payload, sizes=(250, 500, 1000, 2000, 4000, 8000)):
    print(f'{label}:')
    timings = {}
    for n in sizes:
        sql = make_payload(n)
        timings[n] = measure(f'{label} n={n}', sql, sqlparse.parse)

    print()
    print('Scaling ratios (O(n^2) implies ~4x time per 2x input):')
    for prev, curr in zip(sizes, sizes[1:]):
        if timings[prev] > 0:
            ratio = timings[curr] / timings[prev]
            print(f'  n={prev} -> n={curr} (input x{curr / prev:.1f}): '
                  f'time ratio = {ratio:.2f}x')
    print()


run_scaling('Unmatched dollar-quote openers', make_dollar_quote_payload)
run_scaling('Unclosed multiline comments', make_comment_payload)
