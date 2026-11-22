# `c22_stretch_decreasing` — measured

PandasTa issue **#140** (C22-STRETCH-DECREASING), ported 2026-11-22 on branch
`issue-140-c22-stretch-decreasing`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_stretch_decreasing.py` |
| column | `C22STRETCHDEC_100` (`ORD`, integer count in `{0 .. 99}`) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), `SB_BinaryStats_diff_longstretch0` -- "longest period of successive decreases"; reference code pycatch22 1.0.2 and hctsa are **GPL-3.0**, so this was ported from the published definition (binarize the first difference by sign, report the longest run of the "did not increase" state), never from that code |
| tests | `tests/test_c22_stretch_decreasing.py` (90 tests) |
| harness | `docs/measure_c22_stretch_decreasing.py` (sections gate_a, gate_b, noise_floor, gate_c_d, cost, engineered_boundary) |
| Gate A | 8 hand-derived windows match by construction; 1,400/1,400 fired bars on three frames (walk, tick-rounded, ar1) bit-equal to an independent `itertools.groupby` oracle sharing no code or constant with the module — §A |
| Gate B | real module leaks 0/34 offsets (8 random splices each) on three frames; the PRIMARY proof is a single hand-engineered window where a one-bar look-ahead must read 5 instead of the correct 4 -- all four equivalent one-bar mutants caught there. The generic sweep catches those same mutants on only 1-2 of 34 offsets, because the column is tie-heavy (3-6 distinct values per frame, Gate C) -- measured and explained, not hidden — §B |
| Gate C | fires on every bar with a full window (1,400/1,500) on four frames; 3-6 distinct values per frame; the tick-rounded `penny` frame (>10% exactly-zero returns) still fires everywhere with 4 distinct values — §C |
| Gate D | bit-identical (`==`, not a tolerance) under ×8/×64 price rescale, under ×10/×3.7/×0.1 price rescale (not a power of two), AND under ×10/×3.7/×0.1/×2.5 rescale of the RETURNS themselves -- stronger than the usual tolerance claim, because the statistic depends only on the SIGN of each diff; `0 < fires < n` on all stochastic frames — §D |
| Gate E | pending, run by issue-solver after this session |
| Gate F | targeted PandasTa run green: see §F below; full suites run by issue-solver in clean worktrees |

Every number below was produced by
`python docs/measure_c22_stretch_decreasing.py` or by
`python -m pytest tests/test_c22_stretch_decreasing.py`, on this machine
(numpy 1.26.4, pandas 2.3.3, Python 3.11).

---

## 0. What the column is

```
r[t]              = close[t] / close[t-1] - 1
d[i]              = r[i] - r[i-1],  i = T-99 .. T   (99 diffs over 100 returns)
C22STRETCHDEC_100 = longest run of consecutive (d[i] < 0), i.e. of
                    successive strict decreases in the trailing 100 returns,
                    or 0 when the window's own return span is <= 9.09e-13
                    (float-rounding floor on an exactly flat window)
```

catch22's own pipeline z-scores every window before every feature. Z-scoring
is `(x - mean(x)) / sd(x)`, an affine map with a positive slope for
`sd(x) > 0`: `diff(a*x + b) = a * diff(x)`, and multiplying by a positive `a`
cannot flip a sign. So the z-score is **inert** for this feature by
construction, and the module skips it rather than computing and discarding
it. This is also why Gate D's claim is stronger than this fork's usual
return-based catch22 ports (§D).

One reading the definition does not pin, decided explicitly: "falling" is
read as the STRICT sign `d[i] < 0`. A diff of exactly zero (two equal, or
two repeated-zero, returns -- the issue's own BIST tick-rounding worry) is
FLAT, not falling, and breaks the run.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa selected for time-series
CLASSIFICATION performance across 93 problems (Lubba et al. 2019). That is
not return prediction, and nothing here tests it on BIST: its presence in
this fork is existence, not evidence. The prototype measurement in the
issue (Gate E 0.2697 vs `ZIGZAG`, screen round 3) is of the prototype, which
called the real `pycatch22` package only to measure on the owner's machine
-- not of this port, which never imports it.

## A. Gate A — correctness

### A1. Eight hand-derived windows

| returns | expected | got |
|---|---|---|
| `[5,4,3,2,1]` (strictly falling) | 4 | 4 |
| `[1,2,3,4,5]` (strictly rising) | 0 | 0 |
| `[1,1,1,1,1]` (constant: flat, not falling) | 0 | 0 |
| `[3,2,1,2,3,2,1,0]` (runs of 2 and 3) | 3 | 3 |
| `[1,0,1,0,1,0,1,0]` (alternating) | 1 | 1 |
| `[5,4,3,3,2,1]` (flat step mid-fall) | 2 | 2 |
| `[0,0,5,4,3,2,1]` (run at the far end) | 4 | 4 |
| `[5,4,3,2,1,0,0]` (run then flat) | 5 | 5 |

All eight OK (`docs/measure_c22_stretch_decreasing.py` §Gate A1).

### A2. Against an independent `itertools.groupby` oracle, window by window

The oracle (`oracle_series`/`longest_falling_run`) shares no array machinery
or constant (not even `NOISE_FLOOR`) with the module: a plain Python loop
over explicit slices, `itertools.groupby(diff(x) < 0)`.

| frame | windows | bit-equal | windows reaching the floor |
|---|---|---|---|
| walk | 1,400 | 1,400 | 0 |
| tick-rounded | 1,400 | 1,400 | 0 |
| ar1(+0.6) | 1,400 | 1,400 | 0 |

The floor never fires on these frames, so the agreement is evidence rather
than a shared branch.

### A3. The attainable set

`k` consecutive strictly-falling returns among zeros reaches exactly `k`,
for every `k` from 1 to 99 (constructed, not sampled).

## B. Gate B — causality

### B1. The primary proof: a single engineered window

15 alternating returns `[0,10]*7 + [0]` (no run of negative diffs longer
than 1), then a strictly decreasing tail of 5 values `[9,8,7,6,5]` (a run of
4), then one more strictly smaller value `4`. The window ending just BEFORE
that last value must read 4; the window ending AT it must read 5:

```
R = [0,10,0,10,0,10,0,10,0,10,0,10,0,10,0, 9,8,7,6,5, 4]
bar 20 (R[0:20])  -> 4   (correct: the tail run is 4 diffs)
bar 21 (R[1:21])  -> 5   (correct: the tail run extends to 5)
```

All four equivalent one-bar-forward mutants (`write-back-dated`,
`forward-return`, `forward-diff-sign`, `forward-window`), each
`importlib`-read off the module's source and `exec`'d in memory, report **5**
at bar 20 -- the next bar's correct answer, read one bar early.

### B2. The generic future-perturbation sweep (secondary; see why it is weak)

34 offsets, 8 independent random splices each, on three frames (`walk`,
`tick-rounded`, `ar1(+0.6)`):

| | walk | tick-rounded | ar1(+0.6) |
|---|---|---|---|
| real module | 0/34 | 0/34 | 0/34 |
| `write-back-dated` | 1/34 | 2/34 | 1/34 |
| `forward-return` | 1/34 | 2/34 | 1/34 |
| `forward-diff-sign` | 1/34 | 2/34 | 1/34 |
| `forward-window` | 1/34 | 2/34 | 1/34 |
| `forward-span` | 0/34 | 0/34 | 0/34 |

The real module is clean on every frame. The four one-bar mutants are each
caught only 1-2 times of 34: Gate C measures this column at 3-6 distinct
values per frame (far more tie-heavy than a continuous statistic like
`ts_strike_20`'s window mean), so a one-bar perturbation usually lands away
from whichever segment holds the window's own longest run and changes
nothing. This is why §B1's engineered window, not this sweep, is the
load-bearing Gate B evidence.

### B3. The span-guard mutant (`forward-span`)

Needs a degenerate window to be forced live: on a walk carrying
`length + 1` identical closes ending at each of the 34 offsets, the real
module still leaks 0/34 and the mutant is caught 1/34 (the same tie-density
limitation as B2, not a different mechanism).

## The noise floor

An exactly geometric path has mathematically CONSTANT returns -- the answer
is 0 -- but float64 gives it a return span of 8.9e-16 to 4.4e-16 (three
ladders tested), all below the 9.095e-13 floor, so the guarded column reads
0/0/0 (200 of 300 bars fire on each, the rest are the `length`-bar warm-up).
On a walk and a tick-rounded walk (300 bars each) the floor fires on 0 of
200 windows -- it costs nothing on real-shaped data. Against a monotone
one-tick-per-bar path: at price 50 / tick 0.01 the span clears the floor
(3.6e-06) and the column correctly reads 99 (the maximum, since the whole
window IS one long decline); at price 1e6 the span (2.2e-16 to 1.0e-14)
sits below the floor and the column reads 0 instead of the near-maximal run
the mathematics would otherwise give -- the honest cost, stated rather than
hidden.

## C. Gate C — reachability

| frame | fires | distinct | values | counts |
|---|---|---|---|---|
| walk | 1,400/1,500 | 3 | 2,3,4 | 71, 276, 1053 |
| tick-rounded | 1,400/1,500 | 6 | 2,3,4,5,6,7 | 57, 646, 408, 99, 4, 186 |
| ar1(+0.6) | 1,400/1,500 | 4 | 3,4,5,6 | 86, 626, 544, 144 |
| penny (>10% zero returns) | 1,400/1,500 | 4 | 3,4,5,6 | 274, 638, 388, 100 |

The issue's own worry (BIST tick rounding) is directly addressed by
`penny`: 4 distinct values on every one of its 1,400 fired bars despite
many exactly-repeated returns.

## D. Gate D — scale-free

Bit-identical (`==`), not a tolerance, on every cell tested:

| rescale | frames | result |
|---|---|---|
| price ×8, ×64 | walk, tick-rounded, ar1, penny | 1,400/1,400 bit-equal, all 8 cells |
| price ×10, ×3.7, ×0.1 (not a power of two) | walk, tick-rounded | 1,400/1,400 bit-equal, all 6 cells |
| returns ×10, ×3.7, ×0.1, ×2.5 (affine, positive slope) | walk | 1,400/1,400 bit-equal, all 4 cells |

The returns-rescale result is the stronger-than-usual claim: because the
statistic reads only the SIGN of each diff and `diff(a*r) = a * diff(r)` for
a constant `a > 0`, ANY positive rescale of the returns (not just a price
rescale) cannot flip a sign. `0 < fires < n` holds on every stochastic
frame (1,400 of 1,500).

## F. Gate F — suites

```
python -m pytest -q tests/test_c22_stretch_decreasing.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

1,436 passed, 7 skipped, 1 failed
(`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
-- expected: it fails for `c22_stretch_decreasing` until Gate E is run and
the ledger row is recorded, per `CLAUDE.md`'s "Owed, not failed" rule).

Re-run under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` via
`python docs/measure_c22_stretch_decreasing_cpu.py`: all tests in
`tests/test_c22_stretch_decreasing.py` pass unchanged. Every number this
module's tests pin is a bound, a structural fact (`== 0` leaks, exact
hand-derived integers, bit-identical rescales under exact arithmetic) or an
explicitly-measured count on THIS machine -- none depend on a specific CPU
kernel's rounding, because the statistic never divides or sums floats: it
only compares signs of differences and compares a return span against an
absolute floor via `>`.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Cost

At 400,000 bars: 665 ms wall, 382.3 MB traced peak (one `(rows, length - 1)`
boolean diff matrix plus the run-length loop's `current`/`longest`
accumulators).
