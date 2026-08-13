"""Shared harness for the benchmark scripts in this directory.

Every benchmark describes its workload as a list of :class:`Vector`
objects and hands them to :func:`main`, which takes care of running them,
printing a table and deriving a verdict.  A vector is a payload builder
``n -> sql`` plus the entry point that consumes it, measured over a range
of sizes::

    from _harness import Vector, main

    def wide_select(n):
        return 'SELECT ' + ', '.join(f'col_{i}' for i in range(n)) + ' FROM t'

    VECTORS = [Vector('wide select', wide_select, (500, 1000, 2000, 4000))]

    if __name__ == '__main__':
        sys.exit(main('grouping', VECTORS))

Absolute timings are host dependent, so the verdict is based on growth
instead: a least-squares fit of log(time) over log(n) yields an exponent
of about 1 for linear behaviour and about 2 for quadratic behaviour.
Benchmarks exit non-zero as soon as one vector grows super-linearly,
which makes them usable as a regression check for the DoS advisories
without hard-coding a timing threshold.
"""

import argparse
import math
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass

import sqlparse

DEFAULT_TIMEOUT = 30

#: Midpoint between linear (1.0) and quadratic (2.0) growth.  At or above
#: this the measured code path is reported as super-linear.
SUPERLINEAR_EXPONENT = 1.5

#: Measurements below this are dominated by interpreter noise and are left
#: out of the fit; a vector without enough usable points is inconclusive.
MIN_SIGNIFICANT_MS = 1.0

_LINEAR = 'linear'
_SUPERLINEAR = 'super-linear'
_INCONCLUSIVE = 'inconclusive'


@dataclass
class Vector:
    """One measured code path.

    :param name: Shown as the table heading.
    :param build: Builds the payload for a given size, ``n -> sql``.
    :param sizes: Sizes to measure, ascending.
    :param run: Entry point under test, defaults to :func:`sqlparse.parse`.
    """

    name: str
    build: Callable[[int], str]
    sizes: tuple
    run: Callable[[str], object] = sqlparse.parse


class Timeout(Exception):
    """Raised when a single measurement exceeds the timeout."""


def _alarm_handler(signum, frame):
    raise Timeout


# signal.alarm() is Unix-only; elsewhere a benchmark simply runs to
# completion, which is acceptable for a developer tool.
_CAN_ALARM = hasattr(signal, 'SIGALRM')
if _CAN_ALARM:
    signal.signal(signal.SIGALRM, _alarm_handler)


def measure(run, sql, timeout=DEFAULT_TIMEOUT):
    """Run ``run(sql)`` once, return ``(status, elapsed milliseconds)``.

    The status is ``ok``, ``cap`` when a grouping limit rejected the input
    before the measured path was reached, or ``timeout``.
    """
    if _CAN_ALARM:
        signal.alarm(timeout)
    status = 'ok'
    t0 = time.perf_counter()
    try:
        run(sql)
    except sqlparse.exceptions.SQLParseError:
        status = 'cap'
    except Timeout:
        status = 'timeout'
    finally:
        if _CAN_ALARM:
            signal.alarm(0)
    return status, (time.perf_counter() - t0) * 1000


def _format_size(n_bytes):
    if n_bytes < 10_000:
        return f'{n_bytes} B'
    return f'{n_bytes / 1000:.1f} kB'


def _exponent(points):
    """Least-squares slope of log(time) over log(n) for ``(n, ms)`` pairs.

    Only the largest sizes are fitted.  At small n the linear part of the
    work (lexing the payload) dominates and pulls the slope of a
    quadratic path down towards 1, which is exactly where a regression
    would slip through; the asymptotic end of the range is what the
    verdict should be based on.
    """
    if len(points) < 2:
        return None
    points = points[-max(3, (len(points) + 1) // 2):]
    xs = [math.log(n) for n, _ in points]
    ys = [math.log(ms) for _, ms in points]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance == 0:
        return None
    covariance = sum((x - mean_x) * (y - mean_y)
                     for x, y in zip(xs, ys, strict=True))
    return covariance / variance


def run_vector(vector, timeout=DEFAULT_TIMEOUT):
    """Measure one vector, print its table and return its verdict."""
    print(f'{vector.name}:')
    print(f'  {"n":>8}  {"input":>9}  {"time":>11}  {"ratio":>7}  status')

    points = []
    previous = None
    for n in vector.sizes:
        sql = vector.build(n)
        status, elapsed = measure(vector.run, sql, timeout)
        ratio = f'{elapsed / previous:.2f}x' if previous else '-'
        print(f'  {n:>8}  {_format_size(len(sql)):>9}  {elapsed:>8.1f} ms  '
              f'{ratio:>7}  {status}')
        previous = elapsed
        if status == 'ok' and elapsed >= MIN_SIGNIFICANT_MS:
            points.append((n, elapsed))

    exponent = _exponent(points)
    if exponent is None:
        print('  too few usable measurements  =>  inconclusive\n')
        return _INCONCLUSIVE

    verdict = _SUPERLINEAR if exponent >= SUPERLINEAR_EXPONENT else _LINEAR
    print(f'  scaling exponent {exponent:.2f} '
          f'(1.0 linear, 2.0 quadratic)  =>  {verdict}\n')
    return verdict


def _parse_args(argv, title, vectors):
    parser = argparse.ArgumentParser(
        description=f'sqlparse benchmark: {title}',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--sizes', type=lambda s: tuple(int(p) for p in s.split(',')),
        help='comma-separated sizes, overriding the per-vector defaults')
    parser.add_argument(
        '--timeout', type=int, default=DEFAULT_TIMEOUT,
        help='abort a single measurement after this many seconds')
    parser.add_argument(
        '--vector', action='append', metavar='SUBSTRING',
        help='only run vectors whose name contains SUBSTRING '
             f'(available: {", ".join(v.name for v in vectors)})')
    return parser.parse_args(argv)


def main(title, vectors, note=None, argv=None):
    """Run `vectors` and return a process exit code.

    Exit code 0 means no vector grew super-linearly, 1 means at least one
    did -- i.e. the quadratic behaviour a fix was meant to remove is back.
    """
    args = _parse_args(argv, title, vectors)
    if args.vector:
        wanted = [s.lower() for s in args.vector]
        vectors = [v for v in vectors
                   if any(s in v.name.lower() for s in wanted)]
        if not vectors:
            print(f'No vector matches {args.vector}.')
            return 2

    print(f'sqlparse benchmark: {title}')
    if note:
        print(note)
    print()

    verdicts = [
        run_vector(
            vector if args.sizes is None
            else Vector(vector.name, vector.build, args.sizes, vector.run),
            args.timeout)
        for vector in vectors
    ]

    superlinear = verdicts.count(_SUPERLINEAR)
    inconclusive = verdicts.count(_INCONCLUSIVE)
    if superlinear:
        overall = _SUPERLINEAR
    elif inconclusive:
        overall = f'{_LINEAR} where measurable'
    else:
        overall = _LINEAR
    plural = '' if len(verdicts) == 1 else 's'
    summary = f'{len(verdicts)} vector{plural}, {superlinear} super-linear'
    if inconclusive:
        summary += f', {inconclusive} inconclusive'
    print(f'verdict: {overall}  ({summary})')
    return 1 if superlinear else 0
