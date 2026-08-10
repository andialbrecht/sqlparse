"""Validate that ``group_comments`` scales linearly on comment-only input.

Regression check for the quadratic O(n^2) DoS in ``group_comments``
(sqlparse/engine/grouping.py), reported as GHSA-f2ff-p2ww-7p4p.

A statement made only of single-line comments (``'-- c\\n'`` repeated n times)
lexes in O(n) but ``group_comments`` rescans the O(n) remaining tokens for every
comment token, giving O(n^2) total work. ``group_comments`` runs first in
``group()``, before the ``MAX_GROUPING_TOKENS`` guard, so the token cap does not
protect this vector. The path is reachable via ``sqlparse.parse()`` and
``sqlparse.format(sql, strip_comments=True)``.

This script measures the scaling of the vulnerable path and reports whether the
observed growth is quadratic (vulnerable) or roughly linear (patched).

Run with:  python benchmarks/validate_group_comments_dos.py

Exit code 0 => behaviour looks linear (advisory mitigated).
Exit code 1 => behaviour looks quadratic (advisory reproduced).
"""

import sys
import time

import sqlparse


def payload(n):
    """A comment-only statement of n single-line comments."""
    return '-- c\n' * n


def measure(fn, sql):
    t0 = time.perf_counter()
    fn(sql)
    return (time.perf_counter() - t0) * 1000


def run(label, fn):
    print(f'{label}:')
    sizes = (1000, 2000, 4000, 8000)
    timings = []
    for n in sizes:
        dt = measure(fn, payload(n))
        timings.append(dt)
        print(f'  n={n:5d}  {dt:8.1f} ms  ({len(payload(n))} B)')

    # For each doubling of the input, quadratic growth ~4x, linear ~2x.
    ratios = [b / a for a, b in zip(timings, timings[1:]) if a > 0]
    print(f'  doubling ratios: {", ".join(f"{r:.2f}x" for r in ratios)}')
    return ratios


def classify(ratios):
    """Quadratic if the average per-doubling ratio is closer to 4x than 2x."""
    if not ratios:
        return 'inconclusive', 0.0
    avg = sum(ratios) / len(ratios)
    # Midpoint between linear (2x) and quadratic (4x) is 3x.
    return ('quadratic' if avg >= 3.0 else 'linear'), avg


def main():
    print('GHSA-f2ff-p2ww-7p4p: quadratic DoS in group_comments\n')

    all_ratios = []
    all_ratios += run('sqlparse.parse', sqlparse.parse)
    print()
    all_ratios += run(
        'sqlparse.format(strip_comments=True)',
        lambda s: sqlparse.format(s, strip_comments=True),
    )
    print()

    verdict, avg = classify(all_ratios)
    print(f'Average doubling ratio: {avg:.2f}x  =>  {verdict}')
    if verdict == 'quadratic':
        print('VULNERABLE: growth is quadratic, advisory reproduced.')
        return 1
    print('OK: growth is roughly linear, advisory mitigated.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
