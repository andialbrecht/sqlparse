# Benchmarks

Scaling benchmarks for the code paths that have carried quadratic-CPU
(DoS) regressions, plus `bench_parse_throughput.py`, which measures
ordinary large SQL rather than an advisory shape.  They are developer
tools, not part of the test suite: they are not run by `pytest` and not
wired into CI.

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
--profile               profile instead of timing, see below
--profile-top N         frames to print per vector (default: 15)
```

`--profile` runs each vector once at its largest size under `cProfile` and
prints the hottest frames by `tottime`, the time spent in the frame itself.
That is the column that names the function to change; `cumtime` mostly
re-reports the callers above it.  Combine with `--vector` to profile a
single path:

```
python benchmarks/bench_parse_throughput.py --profile --vector UNION
```

Profiling makes no scaling claim, so `--profile` always exits 0.

## Output

Each vector prints one row per size and closes with a verdict:

```
wide column lists:
         n      input         time    ratio     kB/s  status
       500     4402 B      12.3 ms        -      358  ok
      1000     8902 B      24.6 ms    2.00x      362  ok
      2000    18.9 kB      49.1 ms    1.99x      385  ok
  scaling exponent 1.00 (1.0 linear, 2.0 quadratic)  =>  linear
```

Absolute timings are host dependent, so the verdict comes from growth
rather than a timing threshold: a least-squares fit of log(time) over
log(n) gives an exponent near 1 for linear and near 2 for quadratic
behaviour.  A script exits non-zero as soon as one vector grows
super-linearly, which makes it usable as a regression check for the
advisories it covers.

`kB/s` is throughput at that size and does not feed the verdict.  It
covers the blind spot growth alone leaves: a change that makes everything
uniformly twice as slow keeps the exponent at 1.0 and is invisible in the
`ratio` column, but halves this one.  Compare it against a run of the same
script on the previous commit, not against the numbers above.

Two caveats when reading a verdict:

- The exponent is diluted by whatever linear work shares the path.  A
  quadratic step behind a large linear one (lexing, typically) can fit
  under the 1.5 threshold at small sizes and still be quadratic; the fit
  uses only the largest sizes for that reason.  If the `ratio` column
  climbs steadily above 2.00x while the verdict says linear, trust the
  ratios and extend `--sizes`.
- A vector sized to stay under `MAX_GROUPING_TOKENS` measures what the
  default limits permit, not whether the path is linear.  The cap bounds
  how far a quadratic path can be pushed; it does not straighten it.

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
