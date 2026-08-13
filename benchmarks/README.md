# Benchmarks

Scaling benchmarks for the code paths that have carried quadratic-CPU
(DoS) regressions.  They are developer tools, not part of the test suite:
they are not run by `pytest` and not wired into CI.

Run one, or all of them at once:

```
python benchmarks/bench_grouping.py
make benchmark
```

Every script accepts the same options:

```
--sizes 100,200,400     comma-separated sizes, overriding the defaults
--timeout SECONDS       abort a single measurement (default: 30)
--vector SUBSTRING      only run matching vectors, repeatable
```

## Output

Each vector prints one row per size and closes with a verdict:

```
wide column lists:
         n      input         time    ratio  status
       500     4402 B      12.3 ms        -  ok
      1000     8902 B      24.6 ms    2.00x  ok
      2000    18.9 kB      49.1 ms    1.99x  ok
  scaling exponent 1.00 (1.0 linear, 2.0 quadratic)  =>  linear
```

Absolute timings are host dependent, so the verdict comes from growth
rather than a timing threshold: a least-squares fit of log(time) over
log(n) gives an exponent near 1 for linear and near 2 for quadratic
behaviour.  A script exits non-zero as soon as one vector grows
super-linearly, which makes it usable as a regression check for the
advisories it covers.

The `status` column is `ok`, `cap` when a grouping limit rejected the
input before the measured path was reached, or `timeout`.  Only `ok` rows
above 1 ms enter the fit; a vector without at least two of them is
reported as `inconclusive`.

## Adding a benchmark

Name the script after the code path it exercises, `bench_<path>.py`, and
keep it to payload builders plus a `VECTORS` list -- running, timing and
reporting live in `_harness.py`:

```python
import sys

from _harness import Vector, main


def wide_select(n):
    return 'SELECT ' + ', '.join(f'col_{i}' for i in range(n)) + ' FROM t'


VECTORS = [Vector('wide select', wide_select, (500, 1000, 2000, 4000))]

if __name__ == '__main__':
    sys.exit(main('my subject', VECTORS, argv=sys.argv[1:]))
```

A `Vector` is a name, a payload builder `n -> sql`, the sizes to measure
and the entry point under test, which defaults to `sqlparse.parse`.  Pass
something else to measure a different one, e.g.
`lambda sql: sqlparse.format(sql, reindent=True)`.
